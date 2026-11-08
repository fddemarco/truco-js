"""Games live in the database only: every request loads, acts and saves (optimistically), the
table deals on requests, presence writes are throttled, idle games are swept."""

import pickle
from datetime import UTC, datetime, timedelta

import pytest
from sqlmodel import Session, select
from structlog.testing import capture_logs

from app.db import get_engine
from app.games import registry
from app.games.session import Conflict, Forbidden, GameSession, NotFound
from app.models import GameRecord, GameStep
from app.truco.config import GameConfig, RuleMode
from app.truco.match import ResultKind
from tests.test_session import seats


def records() -> dict[str, GameRecord]:
    with Session(get_engine()) as db:
        return {r.id: r for r in db.exec(select(GameRecord)).all()}


def step_indexes(game_id: str) -> list[int]:
    with Session(get_engine()) as db:
        rows = db.exec(select(GameStep.index).where(GameStep.game_id == game_id)).all()
    return sorted(rows)


def into_a_mano(game_id: str, humans: int) -> list[str]:
    tokens = [registry.run(game_id, lambda g, s=s: g.join(s)) for s in range(humans)]
    assert registry.run(game_id, lambda g: g.tick(g.deal_at))
    return tokens


@pytest.mark.parametrize("mode", list(RuleMode))
def test_a_game_goes_on_across_requests(data_dir, mode):
    game = registry.create_game(GameConfig(mode=mode), seats(humans=6))
    tokens = into_a_mano(game.id, 6)
    seat = registry.load(game.id).match.hand.to_act
    before = registry.run(game.id, lambda g: g.view(tokens[seat]))

    def play(g: GameSession):
        action = next(a for a in g.match.actions_for(seat) if a.kind == "jugar")
        return g.act(tokens[seat], action, since=before.step)

    after = registry.run(game.id, play, since=before.step)
    # Steps keep counting, and the next request still has the ones it asks for.
    assert [s.index for s in after.steps] == [before.step + 1]
    again = registry.run(game.id, lambda g: g.view(tokens[seat], since=before.step), before.step)
    assert [s.index for s in again.steps] == [before.step + 1]
    assert again.version == after.version


def test_an_unknown_game_is_not_found(data_dir):
    with pytest.raises(NotFound):
        registry.run("nope", lambda g: g.view())


def test_a_refused_move_saves_nothing(data_dir):
    game = registry.create_game(GameConfig(), seats())
    revision = records()[game.id].revision
    with pytest.raises(Forbidden):
        registry.run(game.id, lambda g: g.act("bad token", None))
    assert records()[game.id].revision == revision


def test_a_save_that_lost_the_race_runs_again(data_dir):
    game = registry.create_game(GameConfig(), seats(humans=2))
    calls = []

    def join(g: GameSession) -> str:
        calls.append(g.version)
        if len(calls) == 1:  # another request joins seat 1 meanwhile
            registry.run(game.id, lambda other: other.join(1))
        return g.join(0)

    with capture_logs() as logs:
        registry.run(game.id, join)
    assert calls == [0, 1]  # the second run saw the other join
    assert any(e["event"] == "game.save_conflict" for e in logs)
    stored = registry.load(game.id)
    assert stored.seats[0].joined and stored.seats[1].joined


def test_a_table_that_keeps_changing_is_a_conflict(data_dir):
    game = registry.create_game(GameConfig(), seats(humans=6))

    def busy(g: GameSession) -> None:
        free = next(i for i, s in enumerate(g.seats) if not s.joined)
        registry.run(game.id, lambda other: other.join(free))
        g.join(free + 1)

    with pytest.raises(Conflict):
        registry.run(game.id, busy)


def test_a_request_after_the_wait_deals_and_saves(data_dir, monkeypatch):
    game = registry.create_game(GameConfig(), seats())
    registry.run(game.id, lambda g: g.join(0))
    deal_at = registry.load(game.id).deal_at
    assert deal_at is not None
    assert registry.run(game.id, lambda g: g.match.hand) is None  # not yet
    monkeypatch.setattr(registry, "now_ms", lambda: deal_at)
    registry.run(game.id, lambda g: g.view())  # a spectator's poll is enough
    stored = registry.load(game.id)
    assert stored.match.history or stored.match.hand is not None


def test_presence_is_saved_only_once_it_moved_enough(data_dir, monkeypatch):
    now = [1_000_000]
    monkeypatch.setattr("app.games.session.now_ms", lambda: now[0])
    game = registry.create_game(GameConfig(), seats(humans=2))
    token = registry.run(game.id, lambda g: g.join(0))
    revision = records()[game.id].revision
    now[0] += registry.PRESENCE_SAVE_MS - 1
    registry.run(game.id, lambda g: g.view(token))
    assert records()[game.id].revision == revision
    now[0] += 1
    registry.run(game.id, lambda g: g.view(token))
    assert records()[game.id].revision == revision + 1


def test_only_the_last_manos_steps_are_kept(data_dir):
    game = registry.create_game(GameConfig(), seats())  # seat 0 human, bots elsewhere
    token = registry.run(game.id, lambda g: g.join(0))

    def advance(g: GameSession) -> None:
        if g.match.hand is None:
            g.tick(g.deal_at)
        else:
            g.act(token, g.match.actions_for(0)[0])

    deals: list[int] = []
    for _ in range(500):
        registry.run(game.id, advance)
        stored = registry.load(game.id)
        if stored.match.finished:
            break
        if stored.deal_step is not None and stored.deal_step not in deals:
            deals.append(stored.deal_step)
        if len(deals) == 3:
            break
    assert len(deals) == 3
    # The step before the previous deal is the oldest one left.
    assert step_indexes(game.id)[0] == deals[1] - 1


def test_a_row_that_no_longer_loads_is_dropped(data_dir):
    game = registry.create_game(GameConfig(), seats())
    with Session(get_engine()) as db:
        record = db.get(GameRecord, game.id)
        record.state = pickle.dumps({"not": "a game"})
        db.add(record)
        db.commit()
    with capture_logs() as logs, pytest.raises(NotFound):
        registry.run(game.id, lambda g: g.view())
    assert any(e["event"] == "game.restore_failed" for e in logs)
    assert game.id not in records()


def age(game_id: str, seconds: float) -> None:
    with Session(get_engine()) as db:
        record = db.get(GameRecord, game_id)
        record.updated_at = datetime.now(UTC) - timedelta(seconds=seconds)
        db.add(record)
        db.commit()


def test_idle_and_finished_games_are_swept_with_their_steps(data_dir):
    idle = registry.create_game(GameConfig(), seats())
    registry.run(idle.id, lambda g: g.join(0))
    assert step_indexes(idle.id)
    over = registry.create_game(GameConfig(), seats())
    registry.run(over.id, lambda g: g.match.forfeit(1, ResultKind.ABANDONO) or g._touch())
    live = registry.create_game(GameConfig(), seats())

    age(idle.id, registry.IDLE_TTL_S + 1)
    age(over.id, registry.FINISHED_TTL_S + 1)
    age(live.id, registry.FINISHED_TTL_S + 1)  # not finished: not idle yet
    with capture_logs() as logs:
        registry.create_game(GameConfig(), seats())  # creating a game sweeps
    assert any(e["event"] == "game.swept" and e["count"] == 2 for e in logs)
    assert idle.id not in records() and over.id not in records() and live.id in records()
    assert step_indexes(idle.id) == []
