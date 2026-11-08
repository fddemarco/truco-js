"""GameSession: failing bots, the table's own deal, presence, seat reset and the result
announcement. Applies to both rule modes (session plumbing, not rules) unless a test says so."""

import random

import pytest
from structlog.testing import capture_logs

from app.bots.settings import PRESETS
from app.games import session as sessions
from app.games.characters import Character
from app.games.session import (
    BOT_CUTTER_WAIT_MS,
    HUMAN_CUTTER_WAIT_MS,
    Conflict,
    Forbidden,
    GameSession,
    Seat,
)
from app.games.views import ONLINE_MS
from app.truco.config import GameConfig, RuleMode
from app.truco.match import ResultKind

CHARACTERS = list(Character)


def seats(humans: int = 1) -> list[Seat]:
    return [Seat("human", f"H{i}", CHARACTERS[i]) for i in range(humans)] + [
        Seat("bot", f"Bot {i}", CHARACTERS[i], PRESETS[0].settings) for i in range(humans, 6)
    ]


def new_session(seed: int = 0, humans: int = 1, mode=RuleMode.STRICT) -> GameSession:
    return GameSession("g1", GameConfig(mode=mode), seats(humans), rng=random.Random(seed))


def deal_now(game: GameSession) -> None:
    assert game.deal_at is not None
    assert game.tick(game.deal_at)


def test_a_failing_bot_is_logged_and_plays_a_legal_move(monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("strategy bug")

    monkeypatch.setattr(sessions, "choose_action", broken)
    game = new_session()
    game.join(0)
    with capture_logs() as logs:
        for _ in range(20):  # deal until the bots have to move
            if game.match.hand is None and not game.match.finished:
                deal_now(game)
            if any(e["event"] == "game.bot_failed" for e in logs):
                break
    failed = [e for e in logs if e["event"] == "game.bot_failed"]
    assert failed and failed[0]["legal"]
    # The bots still moved: the game waits on the human or the next deal, not on a bot.
    hand = game.match.hand
    assert hand is None or game.seats[hand.to_act].kind == "human"


def test_the_result_is_announced_once():
    game = new_session()
    game.join(0)
    game.match.forfeit(1, ResultKind.ABANDONO)
    with capture_logs() as logs:
        game._after_change(had_hand=False)
        game._after_change(had_hand=False)
    assert [e.kind for e in game.events].count("resultado") == 1
    assert sum(e["event"] == "game.finished" for e in logs) == 1


# --- the table deals by itself ------------------------------------------------------------


@pytest.mark.parametrize("mode", list(RuleMode))
def test_the_table_deals_once_its_wait_is_over(monkeypatch, mode):
    now = [1_000_000]
    monkeypatch.setattr(sessions, "now_ms", lambda: now[0])
    game = new_session(mode=mode)
    assert game.deal_at is None  # waiting for players
    game.join(0)
    human = game.seats[game.cutter].kind == "human"
    wait = HUMAN_CUTTER_WAIT_MS if human else BOT_CUTTER_WAIT_MS
    assert game.deal_at == now[0] + wait
    assert game.view().deal_at == game.deal_at and game.view().cutter == game.cutter
    assert not game.tick(now[0] + wait - 1)
    assert game.match.hand is None
    assert game.tick(now[0] + wait)
    assert game.match.hand is not None or game.match.history  # dealt (bots may finish it)
    assert game.events[0].kind == "reparto"


def test_only_the_cutter_may_cut_sooner():
    game = new_session(humans=6)
    tokens = [game.join(s) for s in range(6)]
    others = [t for s, t in enumerate(tokens) if s != game.cutter]
    with pytest.raises(Forbidden):
        game.deal(others[0])
    view = game.deal(tokens[game.cutter])
    assert view.phase is not None and view.deal_at is None
    with pytest.raises(sessions.GameError):
        game.deal(tokens[game.cutter])  # a mano is in progress


def test_nothing_is_dealt_while_a_mano_is_in_progress():
    game = new_session(humans=6)
    for s in range(6):
        game.join(s)
    deal_now(game)
    assert game.deal_at is None
    assert not game.tick(10**15)


def test_a_move_returns_the_view_it_leaves():
    game = new_session(humans=6)
    tokens = [game.join(s) for s in range(6)]
    deal_now(game)
    seat = game.match.hand.to_act
    action = next(a for a in game.match.actions_for(seat) if a.kind == "jugar")
    view = game.act(tokens[seat], action, since=game.steps[-1].index)
    assert view.version == game.version and view.me == seat
    assert [s.seat for s in view.steps] == [seat]


# --- seats: presence, reset, character ------------------------------------------------------


def test_presence_follows_views_and_moves(monkeypatch):
    now = [1_000_000]
    monkeypatch.setattr(sessions, "now_ms", lambda: now[0])
    game = new_session(humans=2)
    first = game.join(0)
    assert [s.online for s in game.view().seats][:2] == [True, False]
    now[0] += ONLINE_MS
    assert not game.view().seats[0].online
    game.view(first)  # polling keeps a seat online
    assert game.view().seats[0].online
    assert all(s.online for s in game.view().seats[2:])  # bots are always there


def test_the_host_frees_a_seat_that_lost_its_token():
    game = new_session(humans=2)
    first, second = game.join(0), game.join(1)
    with pytest.raises(Forbidden):
        game.reset_seat("not the host", 1)
    with pytest.raises(Conflict):
        game.reset_seat(game.host_token, 2)  # a bot
    view = game.reset_seat(game.host_token, 1)
    assert not view.seats[1].joined
    with pytest.raises(Forbidden):
        game.view(second)
    again = game.join(1, "Beto")
    assert game.seat_for(again) == 1 and game.seats[1].name == "Beto"
    assert game.seat_for(first) == 0
    assert game.started  # rejoining doesn't restart the game


def test_a_joining_player_keeps_a_free_character():
    game = new_session(humans=2)
    game.join(0, character=CHARACTERS[3])  # seat 3's
    assert game.seats[0].character == CHARACTERS[0]
    game.join(1, character=CHARACTERS[1])  # already theirs
    assert game.seats[1].character == CHARACTERS[1]
    game.seats[2].character = CHARACTERS[0]  # frees seat 2's character
    game.reset_seat(game.host_token, 0)
    free = next(c for c in CHARACTERS if c not in {s.character for s in game.seats})
    game.join(0, character=free)
    assert game.seats[0].character == free
