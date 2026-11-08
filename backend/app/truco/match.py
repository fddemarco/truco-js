"""A partido a 30: deals, mano types, scoreboard, reclamos and sanctions.

Covers 1.3–1.5, 5.5–5.7, 11.7, 15.1, 15.6, 15.9 and 19.2.
The deal is automated, so the reglamento's physical incidents (dealing errors, cutting,
dropped, lost or extra cards) can't happen and are not modelled.
"""

import random
from dataclasses import dataclass, replace
from enum import StrEnum

from app.truco.cards import Card, shuffled_deck
from app.truco.config import GameConfig
from app.truco.hand import Action, ActionKind, Contest, PicaPicaHand
from app.truco.scoring import PICA_PICA_FROM
from app.truco.signals import SenaEvent
from app.truco.table import choose_first_dealer, mano_of, order_from, other, right_of

WARNINGS_TO_LOSE = 2


class HandKind(StrEnum):
    REDONDA = "redonda"
    PICA_PICA = "pica_pica"


class ResultKind(StrEnum):
    DEPORTIVO = "deportivo"
    SANCION = "sancion"


class MatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class MatchResult:
    kind: ResultKind
    winner: int
    score: tuple[int, int]

    @property
    def administrative(self) -> bool:
        return self.kind != ResultKind.DEPORTIVO


@dataclass(frozen=True)
class HandRecord:
    kind: HandKind
    dealer: int
    points: tuple[int, int]


class Match:
    def __init__(
        self,
        first_dealer: int | None = None,
        rng: random.Random | None = None,
        config: GameConfig | None = None,
    ) -> None:
        self.config = config or GameConfig()
        self.rng = rng or random.Random()
        self.dealer = choose_first_dealer(self.rng) if first_dealer is None else first_dealer
        self.score = [0, 0]
        self.pica_pica_started = False
        self.hand: Contest | PicaPicaHand | None = None
        self.hand_kind: HandKind | None = None
        self.history: list[HandRecord] = []
        self.warnings = [0, 0]  # advertencias disciplinarias per team
        self.result: MatchResult | None = None
        # Interactive reclamos about the last mano stay open until the next deal (11.7, 15.9).
        self._claimable: Contest | None = None
        self._last_hand: Contest | PicaPicaHand | None = None
        self._before_last: tuple[list[int], bool] = ([0, 0], False)

    @property
    def finished(self) -> bool:
        return self.result is not None

    @property
    def last_hand(self) -> Contest | PicaPicaHand | None:
        """The last finished mano (its cards stay visible until the next deal)."""
        return self._last_hand

    def next_hand_kind(self) -> HandKind:
        """Pica-pica alternates with redonda after a team reaches 5, until one reaches 25 (15.1).

        With another target, until one is as close to it as 25 is to 30 (scoring).
        """
        if not self.pica_pica_started or max(self.score) >= self.config.scoring.pica_pica_until:
            return HandKind.REDONDA
        last = self.history[-1].kind
        return HandKind.PICA_PICA if last == HandKind.REDONDA else HandKind.REDONDA

    def deal(self, cards: dict[int, list[Card]] | None = None) -> Contest | PicaPicaHand:
        """Start the next mano; this is the cut that closes the last reclamos.

        `cards` overrides the random deal (tests, replays).
        """
        if self.finished:
            raise MatchError("the partido is over")
        if self.hand is not None:
            raise MatchError("a mano is in progress")
        if self._claimable is not None:
            self._claimable.close_claims()
            self._claimable = None
        return self._deal(cards)

    def actions_for(self, seat: int) -> list[Action]:
        if self.hand is not None:
            return self.hand.actions_for(seat)
        if self._claimable is not None:
            return self._claimable.actions_for(seat)
        return []

    def play(self, action: Action, seat: int | None = None) -> None:
        if self.hand is None:
            if action.kind == ActionKind.RECLAMAR and seat is not None:
                if action not in self.actions_for(seat):
                    raise MatchError("no reclamo open for this seat")
                assert self._claimable is not None
                self._claimable.apply(action, seat)
                self._rescore_last_hand()
                return
            raise MatchError("no mano in progress")
        self.hand.apply(action, seat)
        if self.hand.finished:
            self._close_hand(self._hand_points())

    def sena(self, event: SenaEvent) -> None:
        """Interactive señas. A seña from outside the current duelo is interference (15.6)."""
        if not self.config.interactive:
            raise MatchError("timed señas are only played in interactive mode")
        if self.hand is None:
            raise MatchError("no mano in progress")
        if isinstance(self.hand, Contest):
            self.hand.record_sena(event)
            return
        offender = self.hand.record_sena(event)
        if self.hand.finished:
            self._close_hand(self._hand_points())
        if offender is not None and (self.result is None or not self.result.administrative):
            self.warn(offender)

    def warn(self, team: int) -> None:
        """Advertencia disciplinaria; the 2.ª in the partido loses it (19.2)."""
        self._check_open_for_sanctions()
        self.warnings[team] += 1
        if self.warnings[team] >= WARNINGS_TO_LOSE:
            self._end(ResultKind.SANCION, other(team))

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
            self.hand = PicaPicaHand(cards, mano, scores, self.config, self.rng)
        else:
            self.hand = Contest(
                order, cards, pica_pica=False, scores=scores, config=self.config, rng=self.rng
            )
        return self.hand

    def _hand_points(self) -> tuple[int, int]:
        assert self.hand is not None
        return (self.hand.points[0], self.hand.points[1])

    def _close_hand(self, points: tuple[int, int]) -> None:
        assert self.hand_kind is not None and self.hand is not None
        self._before_last = (list(self.score), self.pica_pica_started)
        self._last_hand = self.hand
        if self.config.interactive:
            hand = self.hand
            self._claimable = hand if isinstance(hand, Contest) else hand.duels[-1]
        for t in (0, 1):
            self.score[t] = self.config.scoring.capped(self.score[t], points[t])
        self.history.append(HandRecord(self.hand_kind, self.dealer, points))
        self.hand = None
        self.dealer = right_of(self.dealer)  # 5.7
        if max(self.score) >= PICA_PICA_FROM:
            self.pica_pica_started = True
        for t in (0, 1):
            if self.score[t] >= self.config.scoring.target:
                self._end(ResultKind.DEPORTIVO, t)

    def _rescore_last_hand(self) -> None:
        """A reclamo moved the points of the last mano: score it again (11.7, 11.10)."""
        assert self._last_hand is not None
        before, pica_pica_started = self._before_last
        points = (self._last_hand.points[0], self._last_hand.points[1])
        self.score = [self.config.scoring.capped(before[t], points[t]) for t in (0, 1)]
        self.history[-1] = replace(self.history[-1], points=points)
        self.pica_pica_started = pica_pica_started or max(self.score) >= PICA_PICA_FROM
        if self.result is not None and self.result.administrative:
            return
        self.result = None
        for t in (0, 1):
            if self.score[t] >= self.config.scoring.target:
                self._end(ResultKind.DEPORTIVO, t)

    def _check_open_for_sanctions(self) -> None:
        # Conduct can still change a sporting result (16.8, 19.2).
        if self.result is not None and self.result.administrative:
            raise MatchError("the partido already has an administrative result")

    def _end(self, kind: ResultKind, winner: int) -> None:
        self.result = MatchResult(kind, winner, (self.score[0], self.score[1]))
        self.hand = None
