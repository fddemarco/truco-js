"""Playing a mano redonda or a pica-pica mano (caps. 7, 8, 10–13, 15).

`Contest` plays one mano redonda (6 players) or one duelo de pica-pica (2 players).
`PicaPicaHand` chains the three duelos of a pica-pica mano.

Both expose the same step API, meant for the UI and for RL self-play:
`to_act` (the seat that must act), `legal_actions()`, `apply(action)`, `finished`, `points`.

Simplifications, to be implemented later:
- TODO: cantos fuera de turno and their vencimiento (13.4–13.6). Only the player in turn
  sings, and only the rival that must answer responds.
- TODO: tapar (8.1). Use `me_voy_al_mazo`.
- TODO: envido declarations are automatic and truthful. Not yet modelled: "son buenas",
  false declarations, acreditación and reclamos (11.4–11.8, 15.9).
- TODO: a player of a future duelo leaving by physically joining the mazo (15.5).
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Literal

from app.truco.cards import Card
from app.truco.envido import EnvidoCall, can_call, envido_points, tanto
from app.truco.rounds import Play, hand_winner, round_winner
from app.truco.score import TARGET
from app.truco.table import duel_order, other, team_of
from app.truco.truco import TrucoCall, next_call, truco_points


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


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    card: Card | None = None

    @classmethod
    def play(cls, card: Card) -> "Action":
        return cls(ActionKind.PLAY, card)


class IllegalAction(ValueError):
    pass


@dataclass
class Pending:
    """A canto waiting for an answer."""

    family: Literal["envido", "truco"]
    chanter: int


@dataclass
class EnvidoResult:
    calls: list[EnvidoCall]
    accepted: bool
    team: int
    points: int
    tantos: dict[int, int] = field(default_factory=dict)  # seat -> tanto, when querido
    winner_seat: int | None = None


class Contest:
    """One mano redonda or one duelo de pica-pica."""

    def __init__(
        self,
        seats: Sequence[int],
        hands: Mapping[int, Sequence[Card]],
        *,
        pica_pica: bool,
        scores: tuple[int, int] = (0, 0),
    ) -> None:
        self.seats = list(seats)  # play order; seats[0] is mano
        self.pica_pica = pica_pica
        self.scores = scores  # partido score when this contest started
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

    @property
    def mano(self) -> int:
        return self.seats[0]

    @property
    def to_act(self) -> int | None:
        if self.finished:
            return None
        if self.pending:
            return self._responder(self.pending[-1].chanter)
        return self.turn

    def live_scores(self) -> tuple[int, int]:
        return (self.scores[0] + self.points[0], self.scores[1] + self.points[1])

    def legal_actions(self) -> list[Action]:
        actor = self.to_act
        if actor is None:
            return []
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

    def apply(self, action: Action) -> None:
        if action not in self.legal_actions():
            raise IllegalAction(f"{action} is not legal now")
        actor = self.to_act
        assert actor is not None
        team = team_of(actor)
        kind = action.kind

        if kind == ActionKind.PLAY:
            assert action.card is not None
            self.hands[actor].remove(action.card)
            self.rounds[-1].append((actor, action.card))
            self._advance()
        elif kind in ENVIDO_ACTIONS:
            self.envido_calls.append(ENVIDO_ACTIONS[kind])
            self._sing("envido", actor)
        elif kind in TRUCO_ACTIONS:
            if self.pending and self.pending[-1].family == "truco":
                # Raising as an answer accepts the previous level.
                self.truco_accepted = self.truco_level
                self.truco_holder = team
            self.truco_level += 1
            self._sing("truco", actor)
        elif kind == ActionKind.QUIERO:
            pending = self.pending.pop()
            if pending.family == "envido":
                self._resolve_envido(accepted=True, chanter=pending.chanter)
            else:
                self.truco_accepted = self.truco_level
                self.truco_holder = team
        elif kind == ActionKind.NO_QUIERO:
            pending = self.pending.pop()
            if pending.family == "envido":
                self._resolve_envido(accepted=False, chanter=pending.chanter)
            else:
                self._finish(team_of(pending.chanter))
        elif kind == ActionKind.MAZO:
            self.active.discard(actor)
            if not any(team_of(s) == team for s in self.active):
                self._fold(team)
        elif kind == ActionKind.NOS_VAMOS:
            self.active -= {s for s in self.seats if team_of(s) == team}
            self._fold(team)

        # The player in turn left the mano: once nothing is pending, the next one plays.
        if not self.finished and not self.pending and self.turn not in self.active:
            self._advance()

    # --- internals -------------------------------------------------------------------

    def _after(self, seat: int) -> list[int]:
        i = self.seats.index(seat)
        n = len(self.seats)
        return [self.seats[(i + k) % n] for k in range(1, n)]

    def _responder(self, chanter: int) -> int:
        return next(
            s for s in self._after(chanter) if s in self.active and team_of(s) != team_of(chanter)
        )

    def _envido_open(self) -> bool:
        """Envido can be sung during the first ronda, before any truco is querido (11.2)."""
        return not self.envido_calls and not self.results and self.truco_accepted == 0

    def _envido_actions(self) -> list[Action]:
        return [Action(_ACTION_FOR[c]) for c in EnvidoCall if can_call(self.envido_calls, c)]

    def _truco_raise(self) -> list[Action]:
        call = next_call(self.truco_level)
        return [Action(_ACTION_FOR[call])] if call else []

    def _sing(self, family: Literal["envido", "truco"], actor: int) -> None:
        if self.pending and self.pending[-1].family == family:
            self.pending[-1].chanter = actor  # a raise answers the previous call
        else:
            self.pending.append(Pending(family, actor))

    def _resolve_envido(self, *, accepted: bool, chanter: int) -> None:
        if accepted:
            contenders = [s for s in self.seats if s in self.active]
            tantos = {s: tanto(self.dealt[s]) for s in contenders}
            best = max(tantos.values())
            # Ties go to whoever is closer to mano (11.6): the first in play order.
            winner_seat = next(s for s in contenders if tantos[s] == best)
            team = team_of(winner_seat)
        else:
            tantos, winner_seat, team = {}, None, team_of(chanter)
        points = envido_points(
            self.envido_calls,
            accepted,
            pica_pica=self.pica_pica,
            scores=self.live_scores(),
            winner=team,
        )
        self.envido = EnvidoResult(
            list(self.envido_calls), accepted, team, points, tantos, winner_seat
        )
        self._award(team, points)

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
        while self.pending and not self.finished:
            pending = self.pending.pop()
            if pending.family == "envido":
                self._resolve_envido(accepted=False, chanter=pending.chanter)
        if not self.finished:
            self._finish(other(team))

    def _finish(self, team: int) -> None:
        self.winner = team
        self.finished = True
        self._award(team, truco_points(self.truco_accepted))

    def _award(self, team: int, points: int) -> None:
        self.points[team] += points
        if self.live_scores()[team] >= TARGET:
            # The partido ends right away; pending cantos have no effect (11.10).
            self.finished = True
            self.match_point = True
            self.pending.clear()


class PicaPicaHand:
    """Three successive duelos: 1 vs 1, 2 vs 2, 3 vs 3, with no new deal in between (15.2–15.4)."""

    def __init__(
        self, hands: Mapping[int, Sequence[Card]], mano: int, scores: tuple[int, int] = (0, 0)
    ) -> None:
        self.hands = hands
        self.scores = scores
        self.pairs = duel_order(mano)
        self.duels: list[Contest] = []
        self.points = [0, 0]
        self.finished = False
        self.match_point = False
        self._start_next()

    @property
    def current(self) -> Contest:
        return self.duels[-1]

    @property
    def to_act(self) -> int | None:
        return None if self.finished else self.current.to_act

    def legal_actions(self) -> list[Action]:
        return [] if self.finished else self.current.legal_actions()

    def apply(self, action: Action) -> None:
        if self.finished:
            raise IllegalAction("the pica-pica mano is over")
        duel = self.current
        duel.apply(action)
        if not duel.finished:
            return
        for t in (0, 1):
            self.points[t] += duel.points[t]
        if duel.match_point:
            # A team reached 30: the remaining duelos are not played (15.1).
            self.finished = self.match_point = True
        elif len(self.duels) == len(self.pairs):
            self.finished = True
        else:
            self._start_next()

    def _start_next(self) -> None:
        pair = self.pairs[len(self.duels)]
        scores = (self.scores[0] + self.points[0], self.scores[1] + self.points[1])
        self.duels.append(
            Contest(pair, {s: self.hands[s] for s in pair}, pica_pica=True, scores=scores)
        )
