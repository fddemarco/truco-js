"""Game sessions: a `Match` shared by human seats (with tokens) and bots.

Sessions live in memory, so they are lost when the API restarts. A client may hold several
seat tokens: one device for every human seat is local multiplayer; one token per device is
online multiplayer. After every human move the bots whose turn it is play right away.
"""

import random
import secrets
import threading
import time
from dataclasses import dataclass
from typing import Literal

import structlog

from app.bots.settings import BotSettings
from app.bots.strategy import choose_action
from app.games.characters import Character, draw_team_names
from app.games.schemas import (
    ActionModel,
    CardModel,
    EnvidoStakesView,
    EnvidoView,
    EventView,
    GameView,
    PendingView,
    PlayView,
    ResultView,
    SeatView,
    SenaSeenView,
    SenaView,
    StepView,
)
from app.truco.cards import Card, Suit
from app.truco.config import GameConfig
from app.truco.envido import said_in_order, tanto
from app.truco.hand import Action, ActionKind, Contest, IllegalAction, PicaPicaHand
from app.truco.match import Match, MatchError
from app.truco.rounds import round_winner
from app.truco.signals import BodySpot, Sena, SenaEvent
from app.truco.table import SEATS, across, number_of, seats_across, team_of

log = structlog.get_logger("game")

MAX_EVENTS = 40
MAX_STEPS = 300  # a mano takes far fewer; older steps are dropped
SENA_VISIBLE_MS = 6000


class GameError(ValueError):
    """The move or request is not allowed now (HTTP 400)."""


class Forbidden(GameError):
    """Unknown seat token (HTTP 403)."""


class Conflict(GameError):
    """The seat can't be taken (HTTP 409)."""


@dataclass
class Seat:
    kind: Literal["human", "bot"]
    name: str
    character: Character
    bot: BotSettings | None = None
    token: str | None = None

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


def to_card(model: CardModel) -> Card:
    return Card(model.number, Suit(model.suit))


def card_model(card: Card) -> CardModel:
    return CardModel(number=card.number, suit=str(card.suit))


def to_action(model: ActionModel) -> Action:
    card = to_card(model.card) if model.card else None
    return Action(model.kind, card=card, number=model.number, sena=model.sena)


def action_model(action: Action) -> ActionModel:
    card = card_model(action.card) if action.card else None
    return ActionModel(kind=action.kind, card=card, number=action.number, sena=action.sena)


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
        self.lock = threading.Lock()
        self.version = 0
        self.started = False
        self.events: list[EventView] = []
        self.steps: list[Step] = []
        self._step_events: list[EventView] = []  # since the last step
        self._contest: Contest | None = None  # last contest shown, kept between manos

    # --- requests -------------------------------------------------------------------

    def join(self, seat: int, name: str = "") -> str:
        with self.lock:
            target = self.seats[seat]
            if target.kind != "human" or target.joined:
                raise Conflict(f"seat {seat} is not open")
            target.token = secrets.token_urlsafe(16)
            if name.strip():
                target.name = name.strip()
            log.info("game.joined", game_id=self.id, seat=seat)
            if all(s.joined for s in self.seats):
                # The table shuffles, cuts and deals the first mano like every other one (deal).
                self.started = True
                log.info("game.started", game_id=self.id)
                self._commit(None)  # the table before the first deal
            self._touch()
            return target.token

    def act(self, token: str, action: Action) -> None:
        with self.lock:
            seat = self.seat_for(token)
            if not self.started:
                raise GameError("waiting for players")
            self._apply(seat, action)
            self._run_bots()
            self._touch()

    def deal(self, token: str) -> None:
        with self.lock:
            self.seat_for(token)
            if not self.started or self.match.hand is not None or self.match.finished:
                raise GameError("can't deal now")
            self._deal()
            self._touch()

    def sena(
        self, token: str, sena: Sena, spot: BodySpot, duration_ms: int, target: int | None
    ) -> None:
        with self.lock:
            seat = self.seat_for(token)
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

    def seat_for(self, token: str) -> int:
        for i, seat in enumerate(self.seats):
            if seat.token is not None and secrets.compare_digest(seat.token, token):
                return i
        raise Forbidden("unknown seat token")

    # --- view -----------------------------------------------------------------------

    def view(
        self, token: str | None = None, look: int | None = None, since: int | None = None
    ) -> GameView:
        """The table as `token`'s seat sees it; `look` is the seat its camera is on.

        A seat only sees the señas of the player across it is looking at (and its own), as
        faces on its own side of the table can't be seen. Spectators see every seña.
        The view carries the steps after `since` (see `_steps_for`).
        """
        with self.lock:
            me = self.seat_for(token) if token else None
            view = self._build_view(me, look)
            view.step = self.steps[-1].index if self.steps else -1
            view.steps, view.base = self._steps_for(me, since)
            return view

    def _build_view(self, me: int | None, look: int | None) -> GameView:
        """The table as it is now for seat `me` (None: a spectator)."""
        m = self.match
        hand = m.hand
        contest = self._current_contest()
        seats = [self._seat_view(i, contest) for i in range(SEATS)]
        view = GameView(
            id=self.id,
            mode=self.config.mode,
            version=self.version,
            server_ms=now_ms(),
            started=self.started,
            match_phase=m.phase,
            seats=seats,
            team_names=list(self.team_names),
            score=list(m.score),
            target=self.config.scoring.target,
            malas_max=self.config.scoring.malas_max,
            hand_number=len(m.history) + (1 if hand else 0),
            hand_kind=m.hand_kind if self.started else None,
            dealer=m.dealer,
            phase=hand.phase if hand else None,
            to_act=hand.to_act if hand else None,
            can_deal=self.started and hand is None and not m.finished,
            result=ResultView(kind=m.result.kind, winner=m.result.winner) if m.result else None,
            events=self.events[-MAX_EVENTS:],
            me=me,
        )
        if contest is not None:
            self._fill_contest(view, contest, hand)
        if me is not None:
            focus = look if look is not None and look in seats_across(me) else across(me)
            view.senas = [s for s in view.senas if s.seat in (me, focus)]
            view.my_cards = [card_model(c) for c in self._cards_of(me)]
            if self.started:
                view.actions = [action_model(a) for a in m.actions_for(me)]
            if contest is not None and me in contest.seats:
                view.my_tanto = tanto(contest.dealt[me])
                view.senas_seen = [
                    SenaSeenView(seat=s.seat, sena=s.sena, ronda=s.ronda)
                    for s in contest.senas_seen(me)
                ]
        return view

    def _steps_for(
        self, me: int | None, since: int | None
    ) -> tuple[list[StepView], GameView | None]:
        """The steps after `since`. Without it (a viewer arriving at the table), the current
        mano's steps since the viewer's last move, or since the deal, so the moves they missed
        play out from `base`, the table before them."""
        if since is not None:
            return [self._step_view(s, me) for s in self.steps if s.index > since], None
        if self.match.hand is None:
            return [], None
        deal = next((i for i in range(len(self.steps) - 1, -1, -1) if self.steps[i].deal), None)
        if deal is None:
            return [], None
        start = deal
        for i in range(deal + 1, len(self.steps)):
            if me is not None and self.steps[i].seat == me:
                start = i + 1
        if start == 0 or start >= len(self.steps):
            return [], None
        steps = [self._step_view(s, me) for s in self.steps[start:]]
        return steps, self.steps[start - 1].views[me]

    @staticmethod
    def _step_view(step: Step, me: int | None) -> StepView:
        return StepView(index=step.index, seat=step.seat, events=step.events, view=step.views[me])

    def _fill_contest(self, view: GameView, contest: Contest, hand) -> None:
        view.mano = contest.mano
        view.pie = contest.seats[-1]
        if contest.pica_pica:
            view.duel = list(contest.seats)
        view.rounds = [
            [PlayView(seat=s, card=card_model(c)) for s, c in ronda] for ronda in contest.rounds
        ]
        view.results = list(contest.results)
        view.pending = [
            PendingView(
                family=p.family, chanter=p.chanter, in_turn=p.in_turn, irregular=p.irregular
            )
            for p in contest.pending
        ]
        view.envido_calls = [str(c) for c in contest.envido_calls]
        view.truco_level = contest.truco_level
        view.truco_accepted = contest.truco_accepted
        stakes = contest.envido_stakes()
        if stakes is not None:
            quiero, no_quiero, team = stakes
            view.envido_stakes = EnvidoStakesView(
                quiero=list(quiero), no_quiero=no_quiero, team=team
            )
        if contest.envido:
            e = contest.envido
            view.envido = EnvidoView(
                calls=[str(c) for c in e.calls],
                accepted=e.accepted,
                team=e.team,
                points=e.points,
                winner_seat=e.winner_seat,
                tantos=_said(contest),
            )
        if contest.declaration:
            view.declarations = dict(contest.declaration.declared)
        recent = now_ms() - SENA_VISIBLE_MS
        events = contest.sena_events if hand is not None else []
        view.senas = [
            SenaView(
                seat=e.seat,
                sena=e.sena,
                spot=e.spot,
                target=e.target,
                start_ms=e.start_ms,
                duration_ms=e.duration_ms,
            )
            for e in events
            if e.start_ms + e.duration_ms >= recent
        ]

    def _seat_view(self, seat: int, contest: Contest | None) -> SeatView:
        s = self.seats[seat]
        in_play = contest is not None and seat in contest.seats
        shown = (
            [card_model(c) for c in contest.dealt[seat]]
            if in_play and contest is not None and seat in contest.shown
            else []
        )
        return SeatView(
            seat=seat,
            team=team_of(seat),
            number=number_of(seat),
            name=s.name,
            character=s.character,
            kind=s.kind,
            joined=s.joined,
            in_play=in_play,
            active=in_play and contest is not None and seat in contest.active,
            cards_left=len(self._cards_of(seat)),
            shown=shown,
            played=[card_model(c) for c in self._played(seat)],
        )

    def _played(self, seat: int) -> list[Card]:
        """The cards `seat` played this mano: every duel of a pica-pica hand, kept on the
        table after the mano ends until the next deal."""
        m = self.match
        hand = m.hand if m.hand is not None else (m.last_hand if self._contest else None)
        contests = hand.duels if isinstance(hand, PicaPicaHand) else [hand] if hand else []
        rondas = [ronda for contest in contests for ronda in contest.rounds]
        return [c for ronda in rondas for s, c in ronda if s == seat]

    def _current_contest(self) -> Contest | None:
        hand = self.match.hand
        if isinstance(hand, PicaPicaHand):
            return hand.current
        return hand if hand is not None else self._contest

    def _cards_of(self, seat: int) -> list[Card]:
        hand = self.match.hand
        if isinstance(hand, PicaPicaHand):
            for duel in hand.duels:
                if seat in duel.seats:
                    return list(duel.hands[seat])
            return list(hand.hands[seat])  # their duelo hasn't started
        contest = hand if hand is not None else self._contest
        if contest is None or seat not in contest.seats:
            return []
        return list(contest.hands[seat])

    # --- internals ------------------------------------------------------------------

    def _touch(self) -> None:
        self.version += 1

    def _commit(self, seat: int | None) -> None:
        """Close a step: the events since the last one, and the table as every human seat and
        a spectator see it now, so clients show each move on the table as it was then."""
        events, self._step_events = self._step_events, []
        index = self.steps[-1].index + 1 if self.steps else 0
        viewers = [None, *(i for i, s in enumerate(self.seats) if s.kind == "human")]
        views = {}
        for me in viewers:
            view = self._build_view(me, None)
            view.senas = []  # señas are live, not part of a step
            views[me] = view
        self.steps.append(Step(index, seat, events, views))
        del self.steps[:-MAX_STEPS]

    def _event(self, event: EventView) -> None:
        self.events.append(event)
        self._step_events.append(event)
        del self.events[: -MAX_EVENTS * 2]

    def _deal(self) -> None:
        self.match.deal()
        self._contest = None
        self._event(EventView(kind="reparto", number=len(self.match.history) + 1))
        self._commit(None)
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
        contests = self._all_contests()
        had_envido = {id(c) for c in contests if c.envido is not None}
        had_results = {id(c): len(c.results) for c in contests}
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
        if action.kind == ActionKind.RECLAMAR:
            claimed = next((c for c in contests if c.claims and c.claims[-1][0] == seat), None)
            event.upheld = claimed.claims[-1][1] if claimed else None
        self._event(event)
        for c in contests:
            for i in range(had_results[id(c)], len(c.results)):
                # A ronda closed (7): its winning card's seat, or no seat for a parda.
                winner, top = round_winner(c.rounds[i], team_of)
                seat_won = top if winner is not None else None
                self._event(EventView(seat=seat_won, kind="ronda", number=i + 1))
        for c in contests:
            if c.envido is not None and id(c) not in had_envido:
                e = c.envido
                said = _said(c)
                if e.accepted and not self.config.interactive:
                    # Strict: the engine compared the tantos; say them as the table would hear.
                    for s, n in said.items():
                        kind = "declarar" if n is not None else "son_buenas"
                        self._event(EventView(seat=s, kind=kind, number=n))
                points = [0, 0]
                points[e.team] = e.points
                won = said.get(e.winner_seat) if e.winner_seat is not None else None
                self._event(
                    EventView(seat=e.winner_seat, kind="envido_resuelto", points=points, number=won)
                )
        self._after_change(had_hand)
        self._commit(seat)

    def _after_change(self, had_hand: bool) -> None:
        m = self.match
        if had_hand and m.hand is None and m.history:
            last = m.history[-1]
            self._event(EventView(kind="fin_mano", points=list(last.points)))
            log.info(
                "game.mano_finished", game_id=self.id, points=list(last.points), score=list(m.score)
            )
            self._contest = self._last_contest()
        if m.result is not None and (not self.events or self.events[-1].kind != "resultado"):
            self._event(EventView(kind="resultado", seat=None, points=list(m.score)))
            log.info(
                "game.finished",
                game_id=self.id,
                result=m.result.kind,
                winner=m.result.winner,
                score=list(m.score),
            )

    def _all_contests(self) -> list[Contest]:
        hand = self.match.hand
        if isinstance(hand, PicaPicaHand):
            return list(hand.duels)
        if hand is not None:
            return [hand]
        return [self._contest] if self._contest else []

    def _last_contest(self) -> Contest | None:
        last = self.match.last_hand
        if isinstance(last, PicaPicaHand):
            return last.duels[-1]
        return last

    def _run_bots(self) -> None:
        for _ in range(500):
            hand = self.match.hand
            if hand is None or self.match.finished:
                return
            seat = hand.to_act
            if seat is None or self.seats[seat].kind != "bot":
                return
            settings = self.seats[seat].bot
            assert settings is not None
            self._apply(seat, choose_action(hand, settings, self.rng, seat))


def _said(contest: Contest) -> dict[int, int | None]:
    """The envido as the table heard it: interactive, what was declared; strict, what would
    have been said in turn from the real tantos (11.4, 11.5), never a tanto kept quiet."""
    e = contest.envido
    if e is None or not e.accepted:
        return {}
    if contest.config.interactive:
        return dict(e.tantos)
    real = {s: n for s, n in e.tantos.items() if n is not None}
    return said_in_order(list(real), real)


_games: dict[str, GameSession] = {}
_games_lock = threading.Lock()


def create_game(
    config: GameConfig, seats: list[Seat], team_names: tuple[str, str] | None = None
) -> GameSession:
    with _games_lock:
        game_id = secrets.token_urlsafe(6)
        session = GameSession(game_id, config, seats, team_names=team_names)
        _games[game_id] = session
        log.info(
            "game.created",
            game_id=game_id,
            mode=str(config.mode),
            humans=sum(s.kind == "human" for s in seats),
            bots=sum(s.kind == "bot" for s in seats),
        )
        return session


def get_game(game_id: str) -> GameSession | None:
    return _games.get(game_id)
