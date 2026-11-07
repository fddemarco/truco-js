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

from app.bots.settings import BotSettings
from app.bots.strategy import choose_action
from app.games.schemas import (
    ActionModel,
    CardModel,
    EnvidoView,
    EventView,
    GameView,
    PendingView,
    PlayView,
    ResultView,
    SeatView,
    SenaSeenView,
    SenaView,
)
from app.truco.cards import Card, Suit
from app.truco.config import GameConfig
from app.truco.hand import Action, ActionKind, Contest, IllegalAction, PicaPicaHand
from app.truco.match import Match, MatchError
from app.truco.signals import BodySpot, Sena, SenaEvent
from app.truco.table import SEATS, number_of, team_of

MAX_EVENTS = 40
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
    bot: BotSettings | None = None
    token: str | None = None

    @property
    def joined(self) -> bool:
        return self.kind == "bot" or self.token is not None


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
        self, game_id: str, config: GameConfig, seats: list[Seat], rng: random.Random | None = None
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
        self.match = Match(rng=self.rng, config=config)
        self.lock = threading.Lock()
        self.version = 0
        self.started = False
        self.events: list[EventView] = []
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
            if all(s.joined for s in self.seats):
                self.started = True
                self._deal()
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
                raise GameError(str(e)) from e
            for team in (0, 1):
                if self.match.warnings[team] > warnings[team]:
                    self._event(EventView(seat=seat, kind="interferencia"))
            self._after_change(had_hand=True)
            self._run_bots()
            self._touch()

    def seat_for(self, token: str) -> int:
        for i, seat in enumerate(self.seats):
            if seat.token is not None and secrets.compare_digest(seat.token, token):
                return i
        raise Forbidden("unknown seat token")

    # --- view -----------------------------------------------------------------------

    def view(self, token: str | None = None) -> GameView:
        with self.lock:
            me = self.seat_for(token) if token else None
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
                seats=seats,
                score=list(m.score),
                hand_number=len(m.history) + (1 if hand else 0),
                hand_kind=m.hand_kind if self.started else None,
                dealer=m.dealer,
                to_act=hand.to_act if hand else None,
                can_deal=self.started and hand is None and not m.finished,
                result=ResultView(kind=m.result.kind, winner=m.result.winner) if m.result else None,
                events=self.events[-MAX_EVENTS:],
                me=me,
            )
            if contest is not None:
                self._fill_contest(view, contest, hand)
            if me is not None:
                view.my_cards = [card_model(c) for c in self._cards_of(me)]
                if self.started:
                    view.actions = [action_model(a) for a in m.actions_for(me)]
                if contest is not None and me in contest.seats:
                    view.senas_seen = [
                        SenaSeenView(seat=s.seat, sena=s.sena, ronda=s.ronda)
                        for s in contest.senas_seen(me)
                    ]
            return view

    def _fill_contest(self, view: GameView, contest: Contest, hand) -> None:
        view.mano = contest.mano
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
        if contest.envido:
            e = contest.envido
            view.envido = EnvidoView(
                calls=[str(c) for c in e.calls],
                accepted=e.accepted,
                team=e.team,
                points=e.points,
                winner_seat=e.winner_seat,
                tantos=dict(e.tantos),
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
            kind=s.kind,
            joined=s.joined,
            in_play=in_play,
            active=in_play and contest is not None and seat in contest.active,
            cards_left=len(self._cards_of(seat)),
            shown=shown,
        )

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

    def _event(self, event: EventView) -> None:
        self.events.append(event)
        del self.events[: -MAX_EVENTS * 2]

    def _deal(self) -> None:
        self.match.deal()
        self._contest = None
        self._event(EventView(kind="reparto", number=len(self.match.history) + 1))
        self._run_bots()

    def _apply(self, seat: int, action: Action) -> None:
        had_hand = self.match.hand is not None
        contests = self._all_contests()
        had_envido = {id(c) for c in contests if c.envido is not None}
        try:
            self.match.play(action, seat)
        except (IllegalAction, MatchError) as e:
            raise GameError(str(e)) from e
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
            if c.envido is not None and id(c) not in had_envido:
                e = c.envido
                points = [0, 0]
                points[e.team] = e.points
                self._event(EventView(seat=e.winner_seat, kind="envido_resuelto", points=points))
        self._after_change(had_hand)

    def _after_change(self, had_hand: bool) -> None:
        m = self.match
        if had_hand and m.hand is None and m.history:
            last = m.history[-1]
            self._event(EventView(kind="fin_mano", points=list(last.points)))
            self._contest = self._last_contest()
        if m.result is not None and (not self.events or self.events[-1].kind != "resultado"):
            self._event(EventView(kind="resultado", seat=None, points=list(m.score)))

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


_games: dict[str, GameSession] = {}
_games_lock = threading.Lock()


def create_game(config: GameConfig, seats: list[Seat]) -> GameSession:
    with _games_lock:
        game_id = secrets.token_urlsafe(6)
        session = GameSession(game_id, config, seats)
        _games[game_id] = session
        return session


def get_game(game_id: str) -> GameSession | None:
    return _games.get(game_id)
