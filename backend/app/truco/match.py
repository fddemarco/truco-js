"""A partido a 30: deals, mano types, scoreboard, dealing errors and sanctions.

Covers 1.3–1.5, 5.5–5.7, 6.4, 15.1, 16.4, 19.2 and the result types of 1.14.

TODO: fuerza mayor and substitutes (4.4), suspensions (17.3), interference in pica-pica
(15.6), presentación delays (4.1) and the 15-minute correction window (16.8).
"""

import random
from dataclasses import dataclass
from enum import StrEnum

from app.truco.cards import Card, shuffled_deck
from app.truco.hand import Action, Contest, PicaPicaHand
from app.truco.score import TARGET, capped
from app.truco.table import (
    SEATS,
    choose_first_dealer,
    mano_of,
    order_from,
    other,
    right_of,
    team_of,
)

PICA_PICA_FROM = 5
PICA_PICA_UNTIL = 25
DEALING_PENALTY = 2
DEALING_ERRORS_PER_CYCLE = 2
WARNINGS_TO_LOSE = 2


class HandKind(StrEnum):
    REDONDA = "redonda"
    PICA_PICA = "pica_pica"


class ResultKind(StrEnum):
    DEPORTIVO = "deportivo"
    AUSENCIA = "ausencia"
    DESCALIFICACION = "descalificacion"
    ABANDONO = "abandono"
    SANCION = "sancion"
    DOBLE_DESCALIFICACION = "doble_descalificacion"


class DealingErrorOutcome(StrEnum):
    CONTINUE = "continuar"  # 1.º error, the affected captain keeps the deal
    REDEAL = "repetir"  # 1.º error, the same dealer deals again
    PENALTY = "penalidad"  # 2.º error: +2 to the rival, mano annulled, next dealer


class MatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class MatchResult:
    kind: ResultKind
    winner: int | None  # None only for doble descalificación
    score: tuple[int, int]

    @property
    def administrative(self) -> bool:
        return self.kind != ResultKind.DEPORTIVO


@dataclass(frozen=True)
class HandRecord:
    kind: HandKind
    dealer: int
    points: tuple[int, int]
    annulled: bool = False


class Match:
    def __init__(self, first_dealer: int | None = None, rng: random.Random | None = None) -> None:
        self.rng = rng or random.Random()
        self.dealer = choose_first_dealer(self.rng) if first_dealer is None else first_dealer
        self.score = [0, 0]
        self.pica_pica_started = False
        self.hand: Contest | PicaPicaHand | None = None
        self.hand_kind: HandKind | None = None
        self.history: list[HandRecord] = []
        self.dealing_errors = dict.fromkeys(range(SEATS), 0)  # per dealer, reset each partido
        self.warnings = [0, 0]  # advertencias disciplinarias per team
        self.result: MatchResult | None = None
        self.homologated = False

    @property
    def finished(self) -> bool:
        return self.result is not None

    def next_hand_kind(self) -> HandKind:
        """Pica-pica alternates with redonda after a team reaches 5, until one reaches 25 (15.1)."""
        if not self.pica_pica_started or max(self.score) >= PICA_PICA_UNTIL:
            return HandKind.REDONDA
        last = self.history[-1].kind
        return HandKind.PICA_PICA if last == HandKind.REDONDA else HandKind.REDONDA

    def deal(self, cards: dict[int, list[Card]] | None = None) -> Contest | PicaPicaHand:
        """Start the next mano. `cards` overrides the random deal (tests, replays)."""
        if self.finished:
            raise MatchError("the partido is over")
        if self.hand is not None:
            raise MatchError("a mano is in progress")
        return self._deal(cards)

    def play(self, action: Action) -> None:
        if self.hand is None:
            raise MatchError("no mano in progress")
        self.hand.apply(action)
        if self.hand.finished:
            self._close_hand(tuple(self.hand.points))

    def dealing_error(self, *, repeat: bool = True) -> DealingErrorOutcome:
        """Register an error by the current dealer (6.1–6.4).

        On a 1.º error the affected captain chooses to continue or `repeat`. The 2.º error in
        the dealer's cycle gives the rival 2 points, annuls the mano and passes the deck.
        """
        if self.hand is None:
            raise MatchError("no mano in progress")
        self.dealing_errors[self.dealer] += 1
        if self.dealing_errors[self.dealer] >= DEALING_ERRORS_PER_CYCLE:
            self.dealing_errors[self.dealer] = 0
            points = [0, 0]
            points[other(team_of(self.dealer))] = DEALING_PENALTY
            self._close_hand((points[0], points[1]), annulled=True)
            return DealingErrorOutcome.PENALTY
        if repeat:
            self.hand = None
            self._deal(None)
            return DealingErrorOutcome.REDEAL
        return DealingErrorOutcome.CONTINUE

    def warn(self, team: int) -> None:
        """Advertencia disciplinaria; the 2.ª in the partido loses it (19.2)."""
        self._check_open_for_sanctions()
        self.warnings[team] += 1
        if self.warnings[team] >= WARNINGS_TO_LOSE:
            self._end(ResultKind.SANCION, other(team))

    def disqualify(self, *teams: int) -> None:
        self._check_open_for_sanctions()
        if set(teams) == {0, 1}:
            self._end(ResultKind.DOBLE_DESCALIFICACION, None)
        else:
            (team,) = set(teams)
            self._end(ResultKind.DESCALIFICACION, other(team))

    def forfeit(self, team: int, kind: ResultKind) -> None:
        """Ausencia (4.1) or abandono of `team`."""
        if kind not in (ResultKind.AUSENCIA, ResultKind.ABANDONO):
            raise ValueError(f"not a forfeit: {kind}")
        self._check_open_for_sanctions()
        self._end(kind, other(team))

    def homologate(self) -> MatchResult:
        """Both captains (or the referee) validate: the result is closed (16.4)."""
        if self.result is None:
            raise MatchError("the partido has no result yet")
        self.homologated = True
        return self.result

    # --- internals -------------------------------------------------------------------

    def _deal(self, cards: dict[int, list[Card]] | None) -> Contest | PicaPicaHand:
        mano = mano_of(self.dealer)
        order = order_from(mano)
        if cards is None:
            # One card at a time, starting to the dealer's right (5.5).
            deck = shuffled_deck(self.rng)
            cards = {s: [] for s in order}
            for _ in range(3):
                for s in order:
                    cards[s].append(deck.pop())
        self.hand_kind = self.next_hand_kind()
        scores = (self.score[0], self.score[1])
        if self.hand_kind == HandKind.PICA_PICA:
            self.hand = PicaPicaHand(cards, mano, scores)
        else:
            self.hand = Contest(order, cards, pica_pica=False, scores=scores)
        return self.hand

    def _close_hand(self, points: tuple[int, int], *, annulled: bool = False) -> None:
        assert self.hand_kind is not None
        for t in (0, 1):
            self.score[t] = capped(self.score[t], points[t])
        self.history.append(HandRecord(self.hand_kind, self.dealer, points, annulled))
        self.hand = None
        self.dealer = right_of(self.dealer)  # 5.7
        if max(self.score) >= PICA_PICA_FROM:
            self.pica_pica_started = True
        for t in (0, 1):
            if self.score[t] >= TARGET:
                self._end(ResultKind.DEPORTIVO, t)

    def _check_open_for_sanctions(self) -> None:
        # Conduct before homologation can still change a sporting result (16.8, 19.2).
        if self.homologated:
            raise MatchError("the result is homologated")
        if self.result is not None and self.result.administrative:
            raise MatchError("the partido already has an administrative result")

    def _end(self, kind: ResultKind, winner: int | None) -> None:
        self.result = MatchResult(kind, winner, (self.score[0], self.score[1]))
        self.hand = None
