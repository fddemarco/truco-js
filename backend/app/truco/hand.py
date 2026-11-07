"""Playing a mano redonda or a pica-pica mano (caps. 7, 8, 10–13, 15).

`Contest` plays one mano redonda (6 players) or one duelo de pica-pica (2 players).
`PicaPicaHand` chains the three duelos of a pica-pica mano.

Both expose the same step API, meant for the UI and for RL self-play:
`actions_for(seat)`, `apply(action, seat)`, `to_act` (the seat the game is waiting for),
`finished` and `points`. `legal_actions()` and `apply(action)` default to `to_act`.

The `GameConfig.mode` decides what players may do:
- Strict: only `to_act` acts. Only the player in turn sings, envido is resolved automatically
  and truthfully, and señas are a free probabilistic action (`ActionKind.SENA`).
- Interactive: several players may act at once. Cantos fuera de turno and their lapsing
  (13.4–13.6), irregular cantos and objections (12.3, 12.4), pardon by agreement (10.3, 12.5),
  envido declarations with bluffing (11.4–11.6), reclamos judged by the engine (11.7, 11.8,
  15.9), tapar (8.1), showing cards (9.7), future-duelo concessions (15.5) and timed señas
  with interference (15.6).
"""

import copy
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from app.truco.cards import Card
from app.truco.config import GameConfig
from app.truco.envido import (
    VALID_DECLARATIONS,
    EnvidoCall,
    can_call,
    envido_points,
    provable_tantos,
    tanto,
)
from app.truco.rounds import Play, hand_winner, round_winner
from app.truco.score import TARGET
from app.truco.signals import Sena, SenaEvent, SenaSeen
from app.truco.table import duel_order, other, team_of
from app.truco.truco import LADDER, TrucoCall, next_call, truco_points


class ActionKind(StrEnum):
    PLAY = "jugar"
    ENVIDO = "envido"
    REAL_ENVIDO = "real_envido"
    FALTA_ENVIDO = "falta_envido"
    TRUCO = "truco"
    RETRUCO = "retruco"
    VALE_CUATRO = "vale_cuatro"
    QUIERO = "quiero"
    NO_QUIERO = "no_quiero"
    MAZO = "me_voy_al_mazo"
    NOS_VAMOS = "nos_vamos_al_mazo"
    SENA = "sena"  # strict mode
    DECLARAR = "declarar"  # interactive mode from here on
    SON_BUENAS = "son_buenas"
    RECLAMAR = "reclamar"
    OBJETAR = "objetar"
    PERDON = "pedir_perdon"
    ACEPTAR_PERDON = "aceptar_perdon"
    TAPAR = "tapar"
    MOSTRAR = "mostrar"


ENVIDO_ACTIONS = {
    ActionKind.ENVIDO: EnvidoCall.ENVIDO,
    ActionKind.REAL_ENVIDO: EnvidoCall.REAL_ENVIDO,
    ActionKind.FALTA_ENVIDO: EnvidoCall.FALTA_ENVIDO,
}
TRUCO_ACTIONS = {
    ActionKind.TRUCO: TrucoCall.TRUCO,
    ActionKind.RETRUCO: TrucoCall.RETRUCO,
    ActionKind.VALE_CUATRO: TrucoCall.VALE_CUATRO,
}
_ACTION_FOR = {call: kind for kind, call in (ENVIDO_ACTIONS | TRUCO_ACTIONS).items()}
# Actions that effectively start a duelo de pica-pica (15.9).
STARTING_KINDS = {
    ActionKind.PLAY,
    ActionKind.TAPAR,
    ActionKind.MAZO,
    *ENVIDO_ACTIONS,
    *TRUCO_ACTIONS,
}
# Actions that don't close the window to pardon the last canto.
_KEEP_PARDON = {ActionKind.PERDON, ActionKind.ACEPTAR_PERDON, ActionKind.SENA, ActionKind.MOSTRAR}


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    card: Card | None = None
    number: int | None = None  # DECLARAR
    sena: Sena | None = None  # SENA

    @classmethod
    def play(cls, card: Card) -> "Action":
        return cls(ActionKind.PLAY, card)

    @classmethod
    def declare(cls, number: int) -> "Action":
        return cls(ActionKind.DECLARAR, number=number)

    @classmethod
    def signal(cls, sena: Sena) -> "Action":
        return cls(ActionKind.SENA, sena=sena)


class IllegalAction(ValueError):
    pass


@dataclass
class Pending:
    """A canto waiting for an answer."""

    family: Literal["envido", "truco"]
    chanter: int
    in_turn: bool = True  # sung by the player in turn: blocks play until answered (13.2)
    irregular: bool = False  # retruco/vale cuatro out of sequence or without the right (12.3)
    envido_before: list[EnvidoCall] = field(default_factory=list)
    truco_before: tuple[int, int, int | None] = (0, 0, None)  # level, accepted, holder


@dataclass
class EnvidoResult:
    calls: list[EnvidoCall]
    accepted: bool
    team: int
    points: int
    # seat -> tanto. Strict: the real tantos. Interactive: what was declared (None = son buenas).
    tantos: dict[int, int | None] = field(default_factory=dict)
    winner_seat: int | None = None


@dataclass
class Declaration:
    """Interactive envido declarations, in order from mano (11.4)."""

    order: list[int]
    index: int = 0
    declared: dict[int, int | None] = field(default_factory=dict)
    best: int | None = None  # seat with the winning number so far

    @property
    def current(self) -> int:
        return self.order[self.index]

    @property
    def best_number(self) -> int:
        return -1 if self.best is None else self.declared[self.best] or 0


@dataclass
class _Undo:
    """State before the last canto, for a pardon by agreement (10.3, 12.5)."""

    team: int
    state: tuple
    proposed: bool = False


class Contest:
    """One mano redonda or one duelo de pica-pica."""

    def __init__(
        self,
        seats: Sequence[int],
        hands: Mapping[int, Sequence[Card]],
        *,
        pica_pica: bool,
        scores: tuple[int, int] = (0, 0),
        config: GameConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.seats = list(seats)  # play order; seats[0] is mano
        self.pica_pica = pica_pica
        self.scores = scores  # partido score when this contest started
        self.config = config or GameConfig()
        self.rng = rng or random.Random()
        self.dealt = {s: tuple(hands[s]) for s in self.seats}
        self.hands = {s: list(hands[s]) for s in self.seats}
        self.active = set(self.seats)
        self.rounds: list[list[Play]] = [[]]
        self.results: list[int | None] = []  # ronda winners, None = parda
        self.turn = self.seats[0]
        self.pending: list[Pending] = []
        self.envido_calls: list[EnvidoCall] = []
        self.envido: EnvidoResult | None = None
        self.truco_level = 0  # truco calls made
        self.truco_accepted = 0  # truco calls querido
        self.truco_holder: int | None = None  # team allowed to raise (12.1)
        self.points = [0, 0]
        self.winner: int | None = None  # team that won the truco part of the mano
        self.finished = False
        self.match_point = False  # a team reached 30 during this contest
        self.annulled = False
        self.started = False  # first effective action made (15.9)
        # Interactive mode.
        self.in_mazo: set[int] = set()  # cards put into the mazo: the envido can't be proven (8.3)
        self.tapados: set[int] = set()
        self.shown: set[int] = set()
        self.declaration: Declaration | None = None
        self.claims_open = False
        self.claims: list[tuple[int, bool]] = []  # (seat, upheld)
        self.forfeited_to: int | None = None  # every point of this contest goes to this team
        self.interference_by: int | None = None
        self.sena_events: list[SenaEvent] = []
        self._undo: _Undo | None = None
        # Strict mode señas.
        self._seen: dict[int, list[SenaSeen]] = {}
        self._signalled = False

    @property
    def mano(self) -> int:
        return self.seats[0]

    @property
    def to_act(self) -> int | None:
        if self.finished:
            return None
        if self.declaration:
            return self.declaration.current
        if self._blocking():
            return self._responder(self._answerable().chanter)
        return self.turn

    def live_scores(self) -> tuple[int, int]:
        return (self.scores[0] + self.points[0], self.scores[1] + self.points[1])

    def senas_seen(self, seat: int) -> list[SenaSeen]:
        """Strict mode: the señas `seat` noticed."""
        return list(self._seen.get(seat, []))

    def legal_actions(self, seat: int | None = None) -> list[Action]:
        seat = self.to_act if seat is None else seat
        return [] if seat is None else self.actions_for(seat)

    def actions_for(self, seat: int) -> list[Action]:
        if seat not in self.seats:
            return []
        if self.config.interactive:
            return self._interactive_actions(seat)
        if seat != self.to_act:
            return []
        actions = self._strict_actions(seat)
        if not self._signalled:
            actions += [Action.signal(s) for s in Sena]
        return actions

    def apply(self, action: Action, seat: int | None = None) -> None:
        seat = self.to_act if seat is None else seat
        if seat is None or action not in self.actions_for(seat):
            raise IllegalAction(f"{action} is not legal for seat {seat} now")
        kind = action.kind
        team = team_of(seat)
        if kind in STARTING_KINDS:
            self.started = True
        if kind != ActionKind.SENA:
            self._signalled = False
        if kind in ENVIDO_ACTIONS or kind in TRUCO_ACTIONS:
            self._undo = _Undo(team, self._snapshot())
        elif kind not in _KEEP_PARDON:
            self._undo = None

        if kind == ActionKind.PLAY:
            assert action.card is not None
            self.hands[seat].remove(action.card)
            self.rounds[-1].append((seat, action.card))
            self._lapse_out_of_turn()
            self._advance()
        elif kind in ENVIDO_ACTIONS:
            self._sing_envido(ENVIDO_ACTIONS[kind], seat)
        elif kind in TRUCO_ACTIONS:
            self._sing_truco(LADDER.index(TRUCO_ACTIONS[kind]) + 1, seat)
        elif kind == ActionKind.QUIERO:
            pending = self._answerable()
            self.pending.remove(pending)
            if pending.family == "envido":
                self._accept_envido()
            else:
                self.truco_accepted = self.truco_level
                self.truco_holder = team
        elif kind == ActionKind.NO_QUIERO:
            pending = self._answerable()
            self.pending.remove(pending)
            if pending.family == "envido":
                self._resolve_envido(accepted=False, chanter=pending.chanter)
            else:
                self._finish(team_of(pending.chanter))
        elif kind in (ActionKind.MAZO, ActionKind.TAPAR):
            self._leave(seat, into_mazo=kind == ActionKind.MAZO)
        elif kind == ActionKind.NOS_VAMOS:
            for s in self.seats:
                if team_of(s) == team and s in self.active:
                    self.active.discard(s)
                    self.in_mazo.add(s)
            self._fold(team)
        elif kind == ActionKind.SENA:
            assert action.sena is not None
            self._signal(seat, action.sena)
        elif kind in (ActionKind.DECLARAR, ActionKind.SON_BUENAS):
            self._declare(seat, action.number)
        elif kind == ActionKind.RECLAMAR:
            self._claim(seat)
        elif kind == ActionKind.OBJETAR:
            pending = self._answerable()
            self.pending.remove(pending)
            self.truco_level, self.truco_accepted, self.truco_holder = pending.truco_before
        elif kind == ActionKind.PERDON:
            assert self._undo is not None
            self._undo.proposed = True
        elif kind == ActionKind.ACEPTAR_PERDON:
            assert self._undo is not None
            self._restore(self._undo.state)
            self._undo = None
        elif kind == ActionKind.MOSTRAR:
            self.shown.add(seat)

        # The player in turn left the mano: once nothing blocks, the next one plays.
        if (
            not self.finished
            and not self.declaration
            and not self._blocking()
            and self.turn not in self.active
        ):
            self._advance()

    # --- used by PicaPicaHand and Match -------------------------------------------------

    def award_all_to(self, team: int) -> None:
        """Every point at stake in this contest, now and later, goes to `team` (11.7, 15.6)."""
        total = sum(self.points)
        self.points = [0, 0]
        self.forfeited_to = team
        self._award(team, total)

    def annul(self) -> None:
        """The contest counts 0–0 and is not replayed (15.6)."""
        self.points = [0, 0]
        self.finished = self.annulled = True
        self.pending.clear()
        self.declaration = None

    def concede(self, seat: int) -> None:
        """`seat` already put their cards into the mazo before this duelo started (15.5)."""
        self._leave(seat, into_mazo=True)

    def close_claims(self) -> None:
        self.claims_open = False

    def record_sena(self, event: SenaEvent) -> None:
        """Interactive mode: a seña made by a participant of this contest."""
        if not self.config.interactive:
            raise IllegalAction("timed señas are only played in interactive mode")
        if event.seat not in self.active:
            raise IllegalAction("only active players can make señas (8.1)")
        if event.target is not None and (
            event.target not in self.seats
            or event.target == event.seat
            or team_of(event.target) != team_of(event.seat)
        ):
            raise IllegalAction("a seña can only be aimed at a teammate at the table")
        self.sena_events.append(event)

    def interference(self, team: int) -> None:
        """A player outside this duelo interfered (15.6)."""
        if self.interference_by is None:
            self.interference_by = team
            self.award_all_to(other(team))
        elif self.interference_by != team:
            self.annul()

    # --- strict mode ------------------------------------------------------------------

    def _strict_actions(self, actor: int) -> list[Action]:
        actions: list[Action] = []
        if self.pending:
            actions += [Action(ActionKind.QUIERO), Action(ActionKind.NO_QUIERO)]
            if self.pending[-1].family == "envido":
                actions += self._envido_actions()
            else:
                actions += self._truco_raise()
                if self._envido_open():
                    actions += self._envido_actions()
        else:
            actions += [Action.play(card) for card in self.hands[actor]]
            if self._envido_open():
                actions += self._envido_actions()
            if self.truco_level == 0 or self.truco_holder == team_of(actor):
                actions += self._truco_raise()
        actions.append(Action(ActionKind.MAZO))
        if not self.pica_pica:
            actions.append(Action(ActionKind.NOS_VAMOS))
        return actions

    def _signal(self, seat: int, sena: Sena) -> None:
        """Each teammate notices the seña with probability p, each rival with probability q."""
        self._signalled = True
        ronda = len(self.results)
        for observer in self.seats:
            if observer == seat:
                continue
            same_team = team_of(observer) == team_of(seat)
            chance = self.config.sena_notice_p if same_team else self.config.sena_leak_q
            if self.rng.random() < chance:
                self._seen.setdefault(observer, []).append(SenaSeen(seat, sena, ronda))

    # --- interactive mode ---------------------------------------------------------------

    def _interactive_actions(self, seat: int) -> list[Action]:
        actions: list[Action] = []
        if self._claim_open(seat):
            actions.append(Action(ActionKind.RECLAMAR))
        if self.finished:
            return actions
        if self.declaration:
            if seat == self.declaration.current:
                actions += [Action.declare(n) for n in VALID_DECLARATIONS]
                if self.declaration.best is not None:
                    actions.append(Action(ActionKind.SON_BUENAS))
            return actions
        if seat not in self.active:
            return actions

        team = team_of(seat)
        answerable = self._answerable()
        if answerable and team_of(answerable.chanter) != team:
            # Any active rival may answer; the first valid answer counts (10.1).
            actions += [Action(ActionKind.QUIERO), Action(ActionKind.NO_QUIERO)]
            if answerable.family == "envido":
                actions += self._envido_actions()
            else:
                actions += self._truco_calls()
                if answerable.irregular:
                    actions.append(Action(ActionKind.OBJETAR))
        if self._undo:
            if self._undo.team == team and not self._undo.proposed:
                actions.append(Action(ActionKind.PERDON))
            if self._undo.team != team and self._undo.proposed:
                actions.append(Action(ActionKind.ACEPTAR_PERDON))
        if self._envido_open():
            actions += self._envido_actions()  # in or out of turn, or before a pending truco
        if not self._blocking():
            if seat == self.turn:
                actions += [Action.play(card) for card in self.hands[seat]]
            if not self._has_pending("truco"):
                actions += self._truco_calls()
        actions += [Action(ActionKind.MAZO), Action(ActionKind.TAPAR)]
        if not self.pica_pica:
            actions.append(Action(ActionKind.NOS_VAMOS))
        if seat not in self.shown:
            actions.append(Action(ActionKind.MOSTRAR))
        return list(dict.fromkeys(actions))

    def _truco_calls(self) -> list[Action]:
        """Interactive: any higher level may be sung; skipping one is irregular (12.3)."""
        return [Action(_ACTION_FOR[c]) for c in LADDER[self.truco_level :]]

    def _accept_envido(self) -> None:
        if not self.config.interactive:
            self._resolve_envido(accepted=True, chanter=-1)
            return
        self.declaration = Declaration([s for s in self.seats if s in self.active])

    def _declare(self, seat: int, number: int | None) -> None:
        """First number said counts; a tie goes to whoever declared first, closer to mano (11.6)."""
        d = self.declaration
        assert d is not None
        d.declared[seat] = number
        if number is not None and number > d.best_number:
            d.best = seat
        d.index += 1
        # Players whose team already holds the best number don't need to declare.
        while (
            d.index < len(d.order) and d.best is not None and team_of(d.current) == team_of(d.best)
        ):
            d.index += 1
        if d.index < len(d.order):
            return
        assert d.best is not None
        self.declaration = None
        team = team_of(d.best)
        points = self._envido_value(accepted=True, team=team)
        self.envido = EnvidoResult(list(self.envido_calls), True, team, points, d.declared, d.best)
        self.claims_open = True
        self._award(team, points)

    def _claim_open(self, seat: int) -> bool:
        return (
            self.claims_open
            and self.forfeited_to is None
            and team_of(seat) not in {team_of(s) for s, _ in self.claims}
        )

    def _claim(self, seat: int) -> None:
        """The engine as referee checks the envido declarations against the cards (11.7, 11.8)."""
        e = self.envido
        assert e is not None and e.winner_seat is not None
        team = team_of(seat)
        if team != e.team:
            declared = e.tantos[e.winner_seat]
            # The winner must show cards making exactly that number; not if they are in the mazo.
            upheld = e.winner_seat in self.in_mazo or declared not in provable_tantos(
                self.dealt[e.winner_seat]
            )
        else:
            # A loser's false number only counts if their cards ended up exposed.
            upheld = any(
                team_of(s) != team
                and n is not None
                and self._fully_exposed(s)
                and n not in provable_tantos(self.dealt[s])
                for s, n in e.tantos.items()
            )
        self.claims.append((seat, upheld))
        if upheld:
            self.award_all_to(team)

    def _fully_exposed(self, seat: int) -> bool:
        played = sum(1 for ronda in self.rounds for s, _ in ronda if s == seat)
        return seat in self.shown or played == len(self.dealt[seat])

    def _lapse_out_of_turn(self) -> None:
        """Playing a card makes unanswered cantos fuera de turno lapse (13.5)."""
        for pending in [p for p in self.pending if not p.in_turn]:
            self.pending.remove(pending)
            if pending.family == "envido":
                self.envido_calls = list(pending.envido_before)
            else:
                self.truco_level, self.truco_accepted, self.truco_holder = pending.truco_before

    def _snapshot(self) -> tuple:
        return copy.deepcopy(
            (
                self.pending,
                self.envido_calls,
                self.truco_level,
                self.truco_accepted,
                self.truco_holder,
            )
        )

    def _restore(self, state: tuple) -> None:
        (
            self.pending,
            self.envido_calls,
            self.truco_level,
            self.truco_accepted,
            self.truco_holder,
        ) = copy.deepcopy(state)

    # --- shared -----------------------------------------------------------------------

    def _after(self, seat: int) -> list[int]:
        i = self.seats.index(seat)
        n = len(self.seats)
        return [self.seats[(i + k) % n] for k in range(1, n)]

    def _responder(self, chanter: int) -> int:
        return next(
            s for s in self._after(chanter) if s in self.active and team_of(s) != team_of(chanter)
        )

    def _answerable(self) -> Pending | None:
        """The canto to answer now: a pending envido goes first (11.11, 13.6)."""
        envido = [p for p in self.pending if p.family == "envido"]
        return envido[-1] if envido else (self.pending[-1] if self.pending else None)

    def _has_pending(self, family: str) -> bool:
        return any(p.family == family for p in self.pending)

    def _blocking(self) -> bool:
        """A canto sung in turn must be answered before play continues (13.2)."""
        return any(p.in_turn for p in self.pending)

    def _envido_open(self) -> bool:
        """Envido can be sung during the first ronda, before any truco is querido (11.2)."""
        return not self.envido_calls and not self.results and self.truco_accepted == 0

    def _envido_actions(self) -> list[Action]:
        return [Action(_ACTION_FOR[c]) for c in EnvidoCall if can_call(self.envido_calls, c)]

    def _truco_raise(self) -> list[Action]:
        call = next_call(self.truco_level)
        return [Action(_ACTION_FOR[call])] if call else []

    def _sing_envido(self, call: EnvidoCall, seat: int) -> None:
        existing = next((p for p in self.pending if p.family == "envido"), None)
        if existing:
            existing.chanter = seat  # a raise answers the previous call
        else:
            in_turn = not self.config.interactive or seat == self.turn
            self.pending.append(
                Pending("envido", seat, in_turn, envido_before=list(self.envido_calls))
            )
        self.envido_calls.append(call)

    def _sing_truco(self, level: int, seat: int) -> None:
        team = team_of(seat)
        existing = next((p for p in self.pending if p.family == "truco"), None)
        if existing and team_of(existing.chanter) != team:
            # Raising as an answer accepts the previous level.
            previous = self.truco_level
            self.truco_accepted = previous
            self.truco_holder = team
            existing.chanter = seat
            existing.irregular = level != previous + 1
            existing.truco_before = (previous, previous, team)
        else:
            without_right = self.truco_level > 0 and self.truco_holder != team
            in_turn = not self.config.interactive or seat == self.turn
            self.pending.append(
                Pending(
                    "truco",
                    seat,
                    in_turn,
                    irregular=level != self.truco_level + 1 or without_right,
                    truco_before=(self.truco_level, self.truco_accepted, self.truco_holder),
                )
            )
        self.truco_level = level

    def _envido_value(self, *, accepted: bool, team: int) -> int:
        return envido_points(
            self.envido_calls,
            accepted,
            pica_pica=self.pica_pica,
            scores=self.live_scores(),
            winner=team,
        )

    def _resolve_envido(self, *, accepted: bool, chanter: int) -> None:
        if accepted:
            contenders = [s for s in self.seats if s in self.active]
            tantos: dict[int, int | None] = {s: tanto(self.dealt[s]) for s in contenders}
            best = max(t for t in tantos.values() if t is not None)
            # Ties go to whoever is closer to mano (11.6): the first in play order.
            winner_seat: int | None = next(s for s in contenders if tantos[s] == best)
            team = team_of(winner_seat)
        else:
            tantos, winner_seat, team = {}, None, team_of(chanter)
        points = self._envido_value(accepted=accepted, team=team)
        self.envido = EnvidoResult(
            list(self.envido_calls), accepted, team, points, tantos, winner_seat
        )
        self._award(team, points)

    def _leave(self, seat: int, *, into_mazo: bool) -> None:
        """Irse al mazo or tapar: one player leaving is not the team's answer in redonda (8.5)."""
        self.active.discard(seat)
        (self.in_mazo if into_mazo else self.tapados).add(seat)
        team = team_of(seat)
        if not any(team_of(s) == team for s in self.active):
            self._fold(team)

    def _advance(self) -> None:
        played = {s for s, _ in self.rounds[-1]}
        for s in self._after(self.turn):
            if s in self.active and s not in played:
                self.turn = s
                return
        self._close_round()

    def _close_round(self) -> None:
        winner, starter = round_winner(self.rounds[-1], team_of)
        self.results.append(winner)
        decided = hand_winner(self.results, team_of(self.mano))
        if decided is not None:
            self._finish(decided)
            return
        # After a parda the mano starts (7.6); an inactive starter passes to their right (7.4).
        nxt = self.mano if winner is None else starter
        if nxt not in self.active:
            nxt = next(s for s in self._after(nxt) if s in self.active)
        self.turn = nxt
        self.rounds.append([])

    def _fold(self, team: int) -> None:
        """A whole team left the mano: pending cantos count as rejected (8.5, 15.7)."""
        self.declaration = None
        while self.pending and not self.finished:
            pending = self.pending.pop()
            if pending.family == "envido" and team_of(pending.chanter) != team:
                self._resolve_envido(accepted=False, chanter=pending.chanter)
        if not self.finished:
            self._finish(other(team))

    def _finish(self, team: int) -> None:
        self.winner = team
        self.finished = True
        self._award(team, truco_points(self.truco_accepted))

    def _award(self, team: int, points: int) -> None:
        if self.forfeited_to is not None:
            team = self.forfeited_to
        self.points[team] += points
        if self.live_scores()[team] >= TARGET:
            # The partido ends right away; pending cantos have no effect (11.10).
            self.finished = True
            self.match_point = True
            self.pending.clear()
            self.declaration = None


class PicaPicaHand:
    """Three successive duelos: 1 vs 1, 2 vs 2, 3 vs 3, with no new deal in between (15.2–15.4)."""

    def __init__(
        self,
        hands: Mapping[int, Sequence[Card]],
        mano: int,
        scores: tuple[int, int] = (0, 0),
        config: GameConfig | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.hands = hands
        self.scores = scores
        self.config = config or GameConfig()
        self.rng = rng or random.Random()
        self.pairs = duel_order(mano)
        self.duels: list[Contest] = []
        self.conceded: set[int] = set()  # future-duelo players who joined the mazo (15.5)
        self.finished = False
        self.match_point = False
        self._start_next()

    @property
    def current(self) -> Contest:
        return self.duels[-1]

    @property
    def points(self) -> list[int]:
        return [sum(d.points[t] for d in self.duels) for t in (0, 1)]

    @property
    def to_act(self) -> int | None:
        return None if self.finished else self.current.to_act

    def live_scores(self) -> tuple[int, int]:
        points = self.points
        return (self.scores[0] + points[0], self.scores[1] + points[1])

    def legal_actions(self, seat: int | None = None) -> list[Action]:
        seat = self.to_act if seat is None else seat
        return [] if seat is None else self.actions_for(seat)

    def actions_for(self, seat: int) -> list[Action]:
        if self.finished:
            return []
        duel = self._duel_index(seat)
        now = len(self.duels) - 1
        if duel == now:
            return self.current.actions_for(seat)
        if duel == now - 1:
            return self.duels[duel].actions_for(seat)  # reclamos until this duelo starts
        if duel > now and self.config.interactive and seat not in self.conceded:
            return [Action(ActionKind.MAZO)]
        return []

    def apply(self, action: Action, seat: int | None = None) -> None:
        if self.finished:
            raise IllegalAction("the pica-pica mano is over")
        seat = self.to_act if seat is None else seat
        if seat is None or action not in self.actions_for(seat):
            raise IllegalAction(f"{action} is not legal for seat {seat} now")
        duel = self._duel_index(seat)
        now = len(self.duels) - 1
        if duel == now:
            self.current.apply(action, seat)
        elif duel == now - 1:
            self.duels[duel].apply(action, seat)
            self._after_claim()
        else:
            self.conceded.add(seat)
        self._settle()

    def record_sena(self, event: SenaEvent) -> int | None:
        """Interactive señas. Returns the team that interfered, if any (15.6, C.3)."""
        if event.seat in self.current.seats:
            self.current.record_sena(event)
            return None
        team = team_of(event.seat)
        self.current.interference(team)
        self._settle()
        return team

    def _duel_index(self, seat: int) -> int:
        return next(i for i, pair in enumerate(self.pairs) if seat in pair)

    def _settle(self) -> None:
        if len(self.duels) > 1 and self.current.started:
            self.duels[-2].close_claims()
        if self.current.finished:
            self._after_duel()

    def _after_duel(self) -> None:
        if self.current.match_point or max(self.live_scores()) >= TARGET:
            # A team reached 30: the remaining duelos are not played (15.1).
            self.finished = self.match_point = True
        elif len(self.duels) == len(self.pairs):
            self.finished = True
        else:
            self._start_next()

    def _after_claim(self) -> None:
        if max(self.live_scores()) >= TARGET:
            self.finished = self.match_point = True
        elif not self.current.started:
            # The next duelo hasn't started: deal it again with the corrected score.
            self.duels.pop()
            self._start_next()

    def _start_next(self) -> None:
        pair = self.pairs[len(self.duels)]
        duel = Contest(
            pair,
            {s: self.hands[s] for s in pair},
            pica_pica=True,
            scores=self.live_scores(),
            config=self.config,
            rng=self.rng,
        )
        self.duels.append(duel)
        conceded = [s for s in pair if s in self.conceded]
        if len(conceded) == 2:
            duel.annul()
        elif conceded:
            duel.concede(conceded[0])
        if duel.finished:
            self._after_duel()
