"""Game sessions: a `Match` shared by human seats (with tokens) and bots.

A client may hold several seat tokens: one device for every human seat is local multiplayer;
one token per device is online multiplayer. After every move the bots whose turn it is play
right away. Between manos the table deals by itself at `deal_at` (`tick`, called by
app/games/registry.py on every request); the cutter may cut sooner (`deal`). Whoever created
the game holds the host token, which can free a seat whose player lost their token
(`reset_seat`).

The session knows nothing about storage: app/games/registry.py loads it from the database
for every request and saves it back (`__getstate__` leaves out the lock and the steps, which
are stored one row each).
"""

import random
import secrets
import threading
import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

import structlog

from app.bots.settings import BotSettings
from app.bots.strategy import choose_action
from app.games.characters import Character, draw_team_names
from app.games.schemas import EventView, GameView
from app.games.stats import ENVIDO_CANTOS, PartidoLog
from app.games.views import MAX_EVENTS, build_view, card_model, steps_for
from app.truco.cards import Card
from app.truco.config import GameConfig
from app.truco.hand import Action, ActionKind, Contest, IllegalAction, PicaPicaHand
from app.truco.match import Match, MatchError, MatchResult
from app.truco.rounds import round_winner
from app.truco.signals import BodySpot, Sena, SenaEvent
from app.truco.table import SEATS, team_of

log = structlog.get_logger("game")

MAX_STEPS = 300  # a mano takes far fewer; older steps are dropped
MAX_BOT_MOVES = 500  # bot moves in a row; a whole partido takes fewer
# How long the table waits before dealing the next mano (ms): a bot cutter deals after a pause
# to read the result; a human one gets time to cut (or reclamar), then the table deals anyway.
BOT_CUTTER_WAIT_MS = 2000
HUMAN_CUTTER_WAIT_MS = 10_000


class GameError(ValueError):
    """The move or request is not allowed now (HTTP 400)."""


class Forbidden(GameError):
    """Unknown seat or host token, or not this seat's call (HTTP 403)."""


class NotFound(GameError):
    """No such game (HTTP 404)."""


class Conflict(GameError):
    """The seat can't be taken (HTTP 409)."""


@dataclass
class Seat:
    kind: Literal["human", "bot"]
    name: str
    character: Character
    bot: BotSettings | None = None
    token: str | None = None
    last_seen_ms: int = 0  # the seat's last view or move (presence)

    @property
    def joined(self) -> bool:
        return self.kind == "bot" or self.token is not None


@dataclass
class Step:
    """One move and the events it set off, with the table right after it as each human seat
    (and a spectator, None) saw it."""

    index: int
    seat: int | None  # who moved; None for a deal or the start
    events: list[EventView]
    views: dict[int | None, GameView]

    @property
    def deal(self) -> bool:
        return any(e.kind == "reparto" for e in self.events)


def now_ms() -> int:
    return int(time.time() * 1000)


def _duels(hand: Contest | PicaPicaHand | None) -> list[Contest]:
    if isinstance(hand, PicaPicaHand):
        return list(hand.duels)
    return [hand] if hand is not None else []


class GameSession:
    def __init__(
        self,
        game_id: str,
        config: GameConfig,
        seats: list[Seat],
        rng: random.Random | None = None,
        team_names: tuple[str, str] | None = None,
    ) -> None:
        if len(seats) != SEATS:
            raise GameError("a partido needs six seats")
        if all(s.kind == "bot" for s in seats):
            raise GameError("at least one seat must be human")
        if any(s.kind == "bot" and s.bot is None for s in seats):
            raise GameError("every bot needs settings")
        self.id = game_id
        self.config = config
        self.seats = seats
        self.rng = rng or random.Random()
        self.team_names = team_names or draw_team_names(self.rng)
        self.match = Match(rng=self.rng, config=config)
        self.host_token = secrets.token_urlsafe(16)
        # Reentrant: a move returns the view it leaves, under the same lock.
        self.lock = threading.RLock()
        self.version = 0
        self.started = False
        self.deal_at: int | None = None  # epoch ms the table deals the next mano
        self.events: list[EventView] = []
        self.stats_log = PartidoLog()
        self.steps: list[Step] = []  # the ones loaded for this request (registry)
        self.deal_step: int | None = None  # the index of the last deal's step
        self.previous_deal_step: int | None = None  # the one before (older steps go)
        self._next_step = 0  # step indexes keep counting across a restore
        self._step_events: list[EventView] = []  # since the last step
        self._contest: Contest | None = None  # last contest shown, kept between manos
        self._announced: MatchResult | None = None  # the result last put in the log

    # --- storage ----------------------------------------------------------------------

    def __getstate__(self) -> dict:
        # Steps are many full views: the registry stores each in its own row and loads only
        # the ones a request can need (step indexes go on from `_next_step`).
        state = self.__dict__.copy()
        del state["lock"]
        state["steps"] = []
        return state

    def __setstate__(self, state: dict) -> None:
        self.__dict__.update(state)
        self.lock = threading.RLock()

    # --- requests -------------------------------------------------------------------

    def join(self, seat: int, name: str = "", character: Character | None = None) -> str:
        """Take an open human seat; `character` is kept if no other seat has it."""
        with self.lock:
            target = self.seats[seat]
            if target.kind != "human" or target.joined:
                raise Conflict(f"seat {seat} is not open")
            target.token = secrets.token_urlsafe(16)
            target.last_seen_ms = now_ms()
            if name.strip():
                target.name = name.strip()
            taken = {s.character for i, s in enumerate(self.seats) if i != seat}
            if character is not None and character not in taken:
                target.character = character
            log.info("game.joined", game_id=self.id, seat=seat)
            if not self.started and all(s.joined for s in self.seats):
                # The table shuffles, cuts and deals the first mano like every other one.
                self.started = True
                log.info("game.started", game_id=self.id)
                self._commit(None)  # the table before the first deal
            self._touch()
            return target.token

    def act(
        self, token: str, action: Action, look: int | None = None, since: int | None = None
    ) -> GameView:
        with self.lock:
            seat = self._seen(token)
            if not self.started:
                raise GameError("waiting for players")
            self._apply(seat, action)
            self._run_bots()
            self._touch()
            return self._view(seat, look, since)

    def deal(self, token: str, look: int | None = None, since: int | None = None) -> GameView:
        """The cutter cuts before `deal_at`: the table deals now."""
        with self.lock:
            seat = self._seen(token)
            if not self._can_deal():
                raise GameError("can't deal now")
            if seat != self.cutter:
                raise Forbidden(f"only the cutter (seat {self.cutter}) cuts")
            self._deal()
            self._touch()
            return self._view(seat, look, since)

    def tick(self, now: int) -> bool:
        """Deal if the table's wait is over (`now` in epoch ms). True if it dealt."""
        with self.lock:
            if self.deal_at is None or now < self.deal_at:
                return False
            if not self._can_deal():
                self.deal_at = None
                return False
            self._deal()
            self._touch()
            return True

    def sena(
        self,
        token: str,
        sena: Sena,
        spot: BodySpot,
        duration_ms: int,
        target: int | None,
        look: int | None = None,
        since: int | None = None,
    ) -> GameView:
        with self.lock:
            seat = self._seen(token)
            warnings = list(self.match.warnings)
            try:
                event = SenaEvent(seat, sena, spot, now_ms(), duration_ms, target)
                self.match.sena(event)
            except (ValueError, MatchError) as e:
                log.warning("game.sena_rejected", game_id=self.id, seat=seat, reason=str(e))
                raise GameError(str(e)) from e
            log.info("game.sena", game_id=self.id, seat=seat, duration_ms=duration_ms)
            for team in (0, 1):
                if self.match.warnings[team] > warnings[team]:
                    self._event(EventView(seat=seat, kind="interferencia"))
                    log.warning("game.interference", game_id=self.id, seat=seat, team=team)
            self._after_change(had_hand=True)
            if self._step_events:
                self._commit(seat)
            self._run_bots()
            self._touch()
            return self._view(seat, look, since)

    def reset_seat(self, host_token: str, seat: int) -> GameView:
        """The host frees a human seat (its player lost their token): the old token stops
        working and anyone with the link can take the seat again."""
        with self.lock:
            if not secrets.compare_digest(self.host_token, host_token):
                raise Forbidden("unknown host token")
            target = self.seats[seat]
            if target.kind != "human" or target.token is None:
                raise Conflict(f"seat {seat} is not taken")
            target.token = None
            target.last_seen_ms = 0
            log.info("game.seat_reset", game_id=self.id, seat=seat)
            self._touch()
            return self._view(None, None, None)

    @property
    def next_step(self) -> int:
        """The index the next step gets."""
        return self._next_step

    def seat_for(self, token: str) -> int:
        for i, seat in enumerate(self.seats):
            if seat.token is not None and secrets.compare_digest(seat.token, token):
                return i
        raise Forbidden("unknown seat token")

    def view(
        self, token: str | None = None, look: int | None = None, since: int | None = None
    ) -> GameView:
        """The table as `token`'s seat sees it; `look` is the seat its camera is on.

        A seat only sees the señas of the player across it is looking at (and its own), as
        faces on its own side of the table can't be seen. Spectators see every seña.
        The view carries the steps after `since` (see `views.steps_for`).
        """
        with self.lock:
            me = self._seen(token) if token else None
            return self._view(me, look, since)

    # --- what's on the table ------------------------------------------------------------

    @property
    def cutter(self) -> int:
        """Who cuts the next deal: the player to the dealer's left (the dealer deals to the
        right, 5.5)."""
        return (self.match.dealer + SEATS - 1) % SEATS

    def _table_hand(self) -> Contest | PicaPicaHand | None:
        """The mano in progress, or the last one, kept on the table until the next deal."""
        m = self.match
        if m.hand is not None:
            return m.hand
        return m.last_hand if self._contest is not None else None

    def contest(self) -> Contest | None:
        """The mano (or duelo de pica-pica) in progress, or the last one shown."""
        hand = self.match.hand
        if isinstance(hand, PicaPicaHand):
            return hand.current
        return hand if hand is not None else self._contest

    def cards_of(self, seat: int) -> list[Card]:
        hand = self.match.hand
        if isinstance(hand, PicaPicaHand):
            for duel in hand.duels:
                if seat in duel.seats:
                    return list(duel.hands[seat])
            return list(hand.hands[seat])  # their duelo hasn't started
        contest = self.contest()
        if contest is None or seat not in contest.seats:
            return []
        return list(contest.hands[seat])

    def played(self, seat: int) -> list[Card]:
        """The cards `seat` played this mano: every duel of a pica-pica hand, kept on the
        table after the mano ends until the next deal."""
        rondas = [ronda for c in _duels(self._table_hand()) for ronda in c.rounds]
        return [c for ronda in rondas for s, c in ronda if s == seat]

    # --- internals ------------------------------------------------------------------

    def _seen(self, token: str) -> int:
        seat = self.seat_for(token)
        self.seats[seat].last_seen_ms = now_ms()
        return seat

    def _view(self, me: int | None, look: int | None, since: int | None) -> GameView:
        view = build_view(self, me, look, now_ms())
        view.step = self.steps[-1].index if self.steps else self._next_step - 1
        view.steps, view.base = steps_for(self, me, since)
        return view

    def _can_deal(self) -> bool:
        return self.started and self.match.hand is None and not self.match.finished

    def _touch(self) -> None:
        self.version += 1
        self._schedule()

    def _schedule(self) -> None:
        """Between manos the table deals by itself after a wait; otherwise nothing is due."""
        if not self._can_deal():
            self.deal_at = None
        elif self.deal_at is None:
            human = self.seats[self.cutter].kind == "human"
            self.deal_at = now_ms() + (HUMAN_CUTTER_WAIT_MS if human else BOT_CUTTER_WAIT_MS)

    def _commit(self, seat: int | None) -> None:
        """Close a step: the events since the last one, and the table as every human seat and
        a spectator see it now, so clients show each move on the table as it was then."""
        events, self._step_events = self._step_events, []
        viewers = [None, *(i for i, s in enumerate(self.seats) if s.kind == "human")]
        now = now_ms()
        views = {}
        for me in viewers:
            view = build_view(self, me, None, now)
            view.senas = []  # señas are live, not part of a step
            views[me] = view
        self.steps.append(Step(self._next_step, seat, events, views))
        self._next_step += 1
        del self.steps[:-MAX_STEPS]

    def _event(self, event: EventView) -> None:
        self.stats_log.move(event.seat, event.kind, event.number)
        self.events.append(event)
        self._step_events.append(event)
        del self.events[: -MAX_EVENTS * 2]

    def _deal(self) -> None:
        self.match.deal()
        self._contest = None
        self.deal_at = None
        hand = self.match.hand
        if hand is not None:
            self.stats_log.deal(len(self.match.history) + 1, hand.hands)
        self._event(
            EventView(
                kind="reparto",
                number=len(self.match.history) + 1,
                hand_kind=str(self.match.hand_kind),
            )
        )
        self._commit(None)
        self.previous_deal_step, self.deal_step = self.deal_step, self._next_step - 1
        log.info(
            "game.dealt",
            game_id=self.id,
            hand_number=len(self.match.history) + 1,
            hand_kind=str(self.match.hand_kind),
            dealer=self.match.dealer,
        )
        self._run_bots()

    def _apply(self, seat: int, action: Action) -> None:
        had_hand = self.match.hand is not None
        contests = _duels(self._table_hand())
        had_envido = {id(c) for c in contests if c.envido is not None}
        had_results = {id(c): len(c.results) for c in contests}
        score_before = list(self.match.score)
        try:
            self.match.play(action, seat)
        except (IllegalAction, MatchError) as e:
            log.warning(
                "game.action_rejected",
                game_id=self.id,
                seat=seat,
                kind=str(action.kind),
                reason=str(e),
            )
            raise GameError(str(e)) from e
        log.info(
            "game.action",
            game_id=self.id,
            seat=seat,
            by=self.seats[seat].kind,
            kind=str(action.kind),
            card=str(action.card) if action.card else None,
            number=action.number,
        )
        card = card_model(action.card) if action.card else None
        event = EventView(seat=seat, kind=str(action.kind), card=card, number=action.number)
        if action.kind == ActionKind.SENA:
            event.card = event.number = None  # a seña is private
            event.kind = "sena"
        if str(action.kind) in ENVIDO_CANTOS:
            # What the canto is worth, so everyone knows before it is answered.
            sung = next((c for c in contests if seat in c.seats and c.envido_stakes()), None)
            if sung is not None:
                stakes = sung.envido_stakes()
                assert stakes is not None
                event.stakes = [*stakes[0], stakes[1]]
        if action.kind == ActionKind.RECLAMAR:
            claimed = next((c for c in contests if c.claims and c.claims[-1][0] == seat), None)
            event.upheld = claimed.claims[-1][1] if claimed else None
            log.info(
                "game.reclamo",
                game_id=self.id,
                seat=seat,
                upheld=event.upheld,
                score_before=score_before,
                score_after=list(self.match.score),
            )
        self._event(event)
        for c in contests:
            for i in range(had_results[id(c)], len(c.results)):
                # A ronda closed (7): its winning card's seat, or no seat for a parda.
                winner, top = round_winner(c.rounds[i], team_of)
                seat_won = top if winner is not None else None
                self._event(EventView(seat=seat_won, kind="ronda", number=i + 1))
        for c in contests:
            if c.envido is not None and id(c) not in had_envido:
                self._envido_resolved(c)
        self._after_change(had_hand)
        self._commit(seat)

    def _envido_resolved(self, contest: Contest) -> None:
        e = contest.envido
        assert e is not None
        points = [0, 0]
        points[e.team] = e.points
        # Every player's envido, for the log: strict, the real tantos; interactive, what each
        # declared (None: son buenas).
        tantos: list[int | None] = [None] * len(self.seats)
        for s, n in e.tantos.items():
            tantos[s] = n
        won = e.tantos.get(e.winner_seat) if e.winner_seat is not None else None
        log.info(
            "game.envido_resolved",
            game_id=self.id,
            calls=[str(x) for x in e.calls],
            accepted=e.accepted,
            team=e.team,
            points=e.points,
            winner_seat=e.winner_seat,
        )
        self._event(
            EventView(
                seat=e.winner_seat,
                kind="envido_resuelto",
                points=points,
                number=won,
                tantos=tantos if e.accepted else None,
            )
        )

    def _after_change(self, had_hand: bool) -> None:
        m = self.match
        if had_hand and m.hand is None and m.history:
            last = m.history[-1]
            self._event(EventView(kind="fin_mano", points=list(last.points)))
            log.info(
                "game.mano_finished", game_id=self.id, points=list(last.points), score=list(m.score)
            )
            last_hand = m.last_hand
            self._contest = _duels(last_hand)[-1] if last_hand is not None else None
        if m.result == self._announced:
            return
        if m.result is None:
            # A reclamo moved the last mano's points and nobody reaches the target now.
            log.info("game.result_cleared", game_id=self.id, score=list(m.score))
            self._announced = None
            return
        self._announced = m.result
        self._event(EventView(kind="resultado", seat=None, points=list(m.score)))
        log.info(
            "game.finished",
            game_id=self.id,
            result=m.result.kind,
            winner=m.result.winner,
            score=list(m.score),
        )

    def _run_bots(self) -> None:
        """Bots whose turn it is play now. A bot that fails is logged and plays its first legal
        move instead, so the human whose move was already applied isn't blamed for it and the
        game doesn't stall."""
        for _ in range(MAX_BOT_MOVES):
            hand = self.match.hand
            if hand is None or self.match.finished:
                return
            seat = hand.to_act
            if seat is None or self.seats[seat].kind != "bot":
                return
            if not self._bot_move(hand, seat):
                return
        log.error("game.bot_loop_cap", game_id=self.id, moves=MAX_BOT_MOVES)

    def _bot_move(self, hand: Contest | PicaPicaHand, seat: int) -> bool:
        settings = self.seats[seat].bot
        assert settings is not None
        try:
            self._apply(seat, choose_action(hand, settings, self.rng, seat))
            return True
        except Exception:
            legal: Sequence[Action] = hand.legal_actions(seat)
            log.exception(
                "game.bot_failed",
                game_id=self.id,
                seat=seat,
                phase=str(hand.phase),
                legal=[str(a.kind) for a in legal],
            )
        fallback = next((a for a in legal if a.kind == ActionKind.PLAY), None)
        fallback = fallback or (legal[0] if legal else None)
        if fallback is None:
            return False
        try:
            self._apply(seat, fallback)
            return True
        except Exception:
            log.exception("game.bot_stuck", game_id=self.id, seat=seat)
            return False
