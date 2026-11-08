"""Fun facts about a partido, for the end screen.

The session feeds a `PartidoLog` with every deal (the cards each seat got) and every event;
`facts()` reads it once the partido is over. Text only: the frontend words each fact by its key.

- luckiest / unluckiest: best / worst average hand dealt (sum of truco ranks, Anexo A)
- strongest_hand: the best single hand dealt
- best_tanto: the highest tanto dealt (11.1)
- liar: most bluffs: a truco sung on a hand weaker than the partido's average, an envido sung
  with less than 24 of tanto, or a declared number that isn't the real tanto
- envido_king, rondas: most envidos / rondas won
- loudest: most cantos; prudent: most no quiero and mazo
- manos: how many manos were played (no seat)
"""

from collections import Counter
from dataclasses import dataclass, field
from statistics import mean

from app.truco.cards import Card
from app.truco.envido import tanto

TRUCO_CANTOS = {"truco", "retruco", "vale_cuatro"}
ENVIDO_CANTOS = {"envido", "real_envido", "falta_envido"}
FOLDS = {"no_quiero", "me_voy_al_mazo", "nos_vamos_al_mazo"}
WEAK_TANTO = 24  # an envido sung below this is a farol


@dataclass(frozen=True)
class Fact:
    key: str
    seat: int | None = None
    value: float | None = None
    mano: int | None = None
    cards: tuple[Card, ...] = ()


@dataclass
class PartidoLog:
    # mano number -> seat -> the three cards dealt
    dealt: dict[int, dict[int, list[Card]]] = field(default_factory=dict)
    # (mano number, seat, kind, number) for every move and announcement with a seat
    moves: list[tuple[int, int, str, int | None]] = field(default_factory=list)

    def deal(self, mano: int, hands: dict[int, list[Card]]) -> None:
        self.dealt[mano] = {s: list(cards) for s, cards in hands.items()}

    def move(self, seat: int | None, kind: str, number: int | None = None) -> None:
        if seat is not None and self.dealt:
            self.moves.append((max(self.dealt), seat, kind, number))


def strength(cards: list[Card]) -> int:
    return sum(c.rank for c in cards)


def _most(counts: Counter[int], key: str) -> Fact | None:
    if not counts:
        return None
    # The highest count; ties go to the lowest seat, so the result is stable.
    seat, value = min(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return Fact(key, seat, value) if value > 0 else None


def facts(log: PartidoLog) -> list[Fact]:
    if not log.dealt:
        return []
    out: list[Fact | None] = [Fact("manos", value=len(log.dealt))]

    hands = [(mano, seat, cards) for mano, d in log.dealt.items() for seat, cards in d.items()]
    by_seat: dict[int, list[int]] = {}
    for _, seat, cards in hands:
        by_seat.setdefault(seat, []).append(strength(cards))
    averages = {seat: mean(v) for seat, v in by_seat.items()}
    luckiest = min(averages, key=lambda s: (-averages[s], s))
    unluckiest = min(averages, key=lambda s: (averages[s], s))
    out.append(Fact("luckiest", luckiest, round(averages[luckiest], 1)))
    if unluckiest != luckiest:
        out.append(Fact("unluckiest", unluckiest, round(averages[unluckiest], 1)))

    mano, seat, cards = max(hands, key=lambda h: (strength(h[2]), -h[0], -h[1]))
    out.append(Fact("strongest_hand", seat, strength(cards), mano, tuple(cards)))
    mano, seat, cards = max(hands, key=lambda h: (tanto(h[2]), -h[0], -h[1]))
    out.append(Fact("best_tanto", seat, tanto(cards), mano, tuple(cards)))

    average = mean(strength(c) for _, _, c in hands)
    bluffs: Counter[int] = Counter()
    for mano, seat, kind, number in log.moves:
        cards = log.dealt[mano].get(seat)
        if not cards:
            continue
        if (
            (kind in TRUCO_CANTOS and strength(cards) < average)
            or (kind in ENVIDO_CANTOS and tanto(cards) < WEAK_TANTO)
            or (kind == "declarar" and number is not None and number != tanto(cards))
        ):
            bluffs[seat] += 1
    out.append(_most(bluffs, "liar"))

    def count(kinds: set[str]) -> Counter[int]:
        return Counter(seat for _, seat, kind, _ in log.moves if kind in kinds)

    out.append(_most(count({"envido_resuelto"}), "envido_king"))
    out.append(_most(count({"ronda"}), "rondas"))
    out.append(_most(count(TRUCO_CANTOS | ENVIDO_CANTOS), "loudest"))
    out.append(_most(count(FOLDS), "prudent"))
    return [f for f in out if f is not None]
