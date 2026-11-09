"""Hand strength for envido and truco, pica-pica (one against one) and redonda (three a side).

Compressed to what decides each canto with bots that play local card orders:

- Envido depends only on the hand's tanto (0-7, 20-33): one row per tanto.
- Truco card play depends only on the truco ranks (Anexo A), so a hand is its rank signature
  (502 of them): one row per signature and bot card order (`CardOrder`, both teams use it;
  `random` plays any card in hand with equal chance).

Each row has the win rate at every seat, counted from the mano (pica-pica: 0 mano, 1 pie;
redonda: 0-5, even seats the mano's team), at the deal, and `strength`, their mean: the chance
for a hand dealt to a random seat.

- Pica-pica is exact, over every rival hand: envido by inclusion-exclusion, ties going to the
  mano (11.6); truco by playing every rival hand (and every branch of random play) once per
  pair of signatures (7.2, 7.6).
- Redonda is Monte Carlo: for each tanto (or signature), `--deals` deals of the other five
  hands, the hand played at each seat against the same deal. Envido is the team's best tanto,
  ties going to the player nearer the mano (11.6); truco plays the three rondas (7.2, 7.3,
  7.6). Seeded, so a run is reproducible.

Results replace the experiment's previous rows in the `win_rate` table of the app's database
(SQLite in DATA_DIR, or DATABASE_URL), served by `GET /api/analytics/win-rates`.

    cd backend && uv run python ../experiments/win_rates.py [--format ...] [--policy ...]
"""

import argparse
import random
import sys
import time
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.bots.settings import CardOrder  # noqa: E402
from app.bots.strategy import choose_card  # noqa: E402
from app.truco.cards import Card, new_deck  # noqa: E402
from app.truco.config import Format  # noqa: E402
from app.truco.envido import tanto  # noqa: E402
from app.truco.rounds import hand_winner, round_winner  # noqa: E402
from app.truco.table import SEATS, team_of  # noqa: E402

DECK = new_deck()
HANDS: list[tuple[int, ...]] = list(combinations(range(len(DECK)), 3))  # card indices
MANO, PIE = 0, 1  # pica-pica seats; seat = team
FORMATS = (Format.PICA_PICA, Format.REDONDA)
SEATS_OF = {Format.PICA_PICA: 2, Format.REDONDA: SEATS}


def cards_of(hand: Iterable[int]) -> list[Card]:
    return [DECK[i] for i in hand]


def card_code(card: Card) -> str:
    return f"{card.number}-{card.suit}"


@dataclass
class Tally:
    """Deals won out of `samples`; exact truco weighs each by its chance, so both can be
    fractional."""

    wins: float = 0
    samples: float = 0


@dataclass
class Strength:
    """One row: a tanto's or signature's tallies by seat from the mano."""

    seats: list[Tally] = field(default_factory=list)
    exact: bool = True

    @property
    def by_seat(self) -> list[float]:
        return [t.wins / t.samples for t in self.seats]

    @property
    def strength(self) -> float:
        return sum(self.by_seat) / len(self.seats)


# --- envido -------------------------------------------------------------------------------


def envido_counts() -> list[tuple[int, Counter[int]]]:
    """For every hand in HANDS: its tanto and how many rival hands (disjoint from it) have
    each tanto. Inclusion-exclusion over hands sharing one, two or three of its cards."""
    tantos = [tanto(cards_of(h)) for h in HANDS]
    every: Counter[int] = Counter(tantos)
    by_card: dict[int, Counter[int]] = {}
    by_pair: dict[tuple[int, int], Counter[int]] = {}
    for hand, t in zip(HANDS, tantos, strict=True):
        for c in hand:
            by_card.setdefault(c, Counter())[t] += 1
        for pair in combinations(hand, 2):
            by_pair.setdefault(pair, Counter())[t] += 1
    out = []
    for hand, own in zip(HANDS, tantos, strict=True):
        rivals = Counter(every)
        for c in hand:
            rivals.subtract(by_card[c])
        for pair in combinations(hand, 2):
            rivals.update(by_pair[pair])
        rivals[own] -= 1
        out.append((own, +rivals))
    return out


def pica_pica_envido() -> dict[int, Strength]:
    """Exact, by tanto: the mano (seat 0) wins ties, the pie (seat 1) loses them (11.6)."""
    out: dict[int, Strength] = {}
    for own, rivals in envido_counts():
        row = out.setdefault(own, Strength([Tally(), Tally()]))
        total = sum(rivals.values())
        for seat, wins in enumerate(
            (
                sum(n for t, n in rivals.items() if t <= own),
                sum(n for t, n in rivals.items() if t < own),
            )
        ):
            row.seats[seat].wins += wins
            row.seats[seat].samples += total
    return out


def envido_winner(tantos: Sequence[int]) -> int:
    """Seat (from the mano) with the best tanto; ties go to the one nearer the mano (11.6)."""
    return min(range(len(tantos)), key=lambda s: (-tantos[s], s))


def redonda_envido(deals: int, seed: int) -> dict[int, Strength]:
    """By tanto: for each, `deals` hands with it (uniformly) against five random hands."""
    rng = random.Random(f"{seed}-envido")
    by_cards = {frozenset(h): tanto(cards_of(h)) for h in HANDS}
    with_tanto: dict[int, list[tuple[int, ...]]] = {}
    for hand, t in by_cards.items():
        with_tanto.setdefault(t, []).append(tuple(hand))
    out: dict[int, Strength] = {}
    for own, hands in sorted(with_tanto.items()):
        row = out[own] = Strength([Tally() for _ in range(SEATS)], exact=False)
        for _ in range(deals):
            mine = rng.choice(hands)
            rest = [c for c in range(len(DECK)) if c not in mine]
            dealt = rng.sample(rest, 15)
            others = [by_cards[frozenset(dealt[i : i + 3])] for i in range(0, 15, 3)]
            for seat, tally in enumerate(row.seats):
                tantos = [*others[:seat], own, *others[seat:]]
                tally.samples += 1
                tally.wins += team_of(envido_winner(tantos)) == team_of(seat)
    return out


# --- truco --------------------------------------------------------------------------------

Signature = tuple[int, ...]  # a hand's truco ranks, sorted: all card play depends on


def signature(cards: Iterable[Card]) -> Signature:
    return tuple(sorted(c.rank for c in cards))


def examples() -> dict[Signature, list[Card]]:
    """A hand for each signature: cards of one rank are interchangeable."""
    out: dict[Signature, list[Card]] = {}
    for hand in HANDS:
        cards = cards_of(hand)
        out.setdefault(signature(cards), cards)
    return out


def outcomes(
    mano: Sequence[Card], pie: Sequence[Card], order: CardOrder
) -> list[tuple[float, list[int], int]]:
    """Every way one pica-pica mano can be played card by card with both players on `order`:
    (chance, who acted at each turn, seat that won) (7.2, 7.6). `RANDOM` plays each card in hand
    with equal chance; the other orders are deterministic, so they have a single outcome."""
    out: list[tuple[float, list[int], int]] = []

    def go(hands, leader, plays, results, actors, chance) -> None:
        seat = leader if not plays else 1 - leader
        if order == CardOrder.RANDOM:
            choices = hands[seat]
        else:
            choices = [choose_card(hands[seat], [c for _, c in plays], order, None)]
        for card in choices:
            left = list(hands)
            left[seat] = [c for c in hands[seat] if c is not card]
            now = [*plays, (seat, card)]
            acted = [*actors, seat]
            p = chance / len(choices)
            if len(now) < 2:
                go(left, leader, now, results, acted, p)
                continue
            winner, starter = round_winner(now, team_of)
            done = [*results, winner]
            decided = hand_winner(done, team_of(MANO))
            if decided is not None:
                out.append((p, acted, decided))
            else:  # after a parda the mano starts (7.6)
                go(left, MANO if winner is None else starter, [], done, acted, p)

    go([list(mano), list(pie)], MANO, [], [], [], 1.0)
    return out


def rival_signatures(
    only: Collection[Signature] | None = None,
) -> dict[Signature, Counter[Signature]]:
    """For each hand signature (or those in `only`): how many rival hands have each signature.
    The counts depend only on the hand's ranks."""
    out: dict[Signature, Counter[Signature]] = {}
    for hand in HANDS:
        sig = signature(cards_of(hand))
        if sig in out or (only is not None and sig not in only):
            continue
        taken = set(hand)
        out[sig] = Counter(signature(cards_of(h)) for h in HANDS if taken.isdisjoint(h))
    return out


def pica_pica_truco(
    order: CardOrder, only: Collection[Signature] | None = None
) -> dict[Signature, Strength]:
    """Exact, by signature (or those in `only`): the mano's and the pie's chance over every
    rival hand and every branch of random play."""
    example = examples()
    cache: dict[tuple[Signature, Signature], list[tuple[float, list[int], int]]] = {}
    out: dict[Signature, Strength] = {}
    for sig, counts in rival_signatures(only).items():
        row = out[sig] = Strength([Tally(), Tally()])
        for seat, tally in zip((MANO, PIE), row.seats, strict=True):
            for rival, n in counts.items():
                key = (sig, rival) if seat == MANO else (rival, sig)
                if key not in cache:
                    cache[key] = outcomes(example[key[0]], example[key[1]], order)
                for chance, _, winner in cache[key]:
                    tally.samples += n * chance
                    tally.wins += n * chance * (winner == seat)
    return out


def play_out(hands: Sequence[Sequence[Card]], order: CardOrder, rng: random.Random) -> int:
    """Team that wins a mano with seat 0 mano and every seat on `order` (7.1-7.3, 7.6)."""
    left = [list(h) for h in hands]
    players = len(hands)
    leader, results = 0, []
    while True:
        plays: list[tuple[int, Card]] = []
        for i in range(players):
            seat = (leader + i) % players
            card = choose_card(left[seat], [c for _, c in plays], order, rng)
            left[seat].remove(card)
            plays.append((seat, card))
        winner, starter = round_winner(plays, team_of)
        results.append(winner)
        decided = hand_winner(results, team_of(0))
        if decided is not None:
            return decided
        leader = 0 if winner is None else starter  # after a parda the mano starts (7.6)


def redonda_truco_one(args: tuple[Signature, list[Card], CardOrder, int, int]) -> Strength:
    """`deals` deals of five other hands; the hand plays at each seat against each."""
    sig, mine, order, deals, seed = args
    rng = random.Random(f"{seed}-truco-{order}-{sig}")
    rest = [c for c in DECK if c not in mine]
    row = Strength([Tally() for _ in range(SEATS)], exact=False)
    for _ in range(deals):
        dealt = rng.sample(rest, 15)
        others = [dealt[i : i + 3] for i in range(0, 15, 3)]
        for seat, tally in enumerate(row.seats):
            hands = [*others[:seat], mine, *others[seat:]]
            tally.samples += 1
            tally.wins += play_out(hands, order, rng) == team_of(seat)
    return row


def redonda_truco(
    order: CardOrder, deals: int, seed: int, only: Collection[Signature] | None = None
) -> dict[Signature, Strength]:
    jobs = [
        (sig, cards, order, deals, seed)
        for sig, cards in examples().items()
        if only is None or sig in only
    ]
    if len(jobs) == 1:
        return {jobs[0][0]: redonda_truco_one(jobs[0])}
    with ProcessPoolExecutor() as pool:
        rows = pool.map(redonda_truco_one, jobs, chunksize=4)
        return {job[0]: row for job, row in zip(jobs, rows, strict=True)}


# --- rows ---------------------------------------------------------------------------------


def row(
    fmt: Format,
    canto: str,
    policy: str | None,
    strength: Strength,
    *,
    tanto: int | None = None,
    ranks: Signature | None = None,
) -> dict[str, object]:
    return {
        "format": fmt,
        "canto": canto,
        "policy": policy,
        "tanto": tanto,
        "ranks": None if ranks is None else "-".join(map(str, sorted(ranks, reverse=True))),
        "strength": round(strength.strength, 4),
        "by_seat": [round(r, 4) for r in strength.by_seat],
        "samples": strength.seats[0].samples,
        "exact": strength.exact,
    }


def envido_rows(fmt: Format, deals: int, seed: int) -> list[dict[str, object]]:
    by_tanto = pica_pica_envido() if fmt == Format.PICA_PICA else redonda_envido(deals, seed)
    return [row(fmt, "envido", None, s, tanto=t) for t, s in sorted(by_tanto.items())]


def truco_rows(fmt: Format, order: CardOrder, deals: int, seed: int) -> list[dict[str, object]]:
    if fmt == Format.PICA_PICA:
        by_sig = pica_pica_truco(order)
    else:
        by_sig = redonda_truco(order, deals, seed)
    return [row(fmt, "truco", order.value, s, ranks=sig) for sig, s in sorted(by_sig.items())]


def store(rows: list[dict[str, object]], fmt: Format, canto: str, policy: str | None) -> None:
    """Replace this experiment's rows (format + canto + policy) with `rows`."""
    from sqlalchemy import delete, insert
    from sqlmodel import Session

    from app.db import get_engine
    from app.models import WinRate

    with Session(get_engine()) as session:
        # `== None` compiles to IS NULL (envido has no policy).
        session.execute(
            delete(WinRate).where(
                WinRate.format == fmt, WinRate.canto == canto, WinRate.policy == policy
            )
        )
        if rows:
            session.execute(insert(WinRate), rows)
        session.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--format",
        action="append",
        choices=[f.value for f in FORMATS],
        help="repeatable; default: both",
    )
    parser.add_argument(
        "--policy",
        action="append",
        choices=[o.value for o in CardOrder],
        help="truco: card order every player uses (repeatable; default: all of them)",
    )
    parser.add_argument(
        "--deals", type=int, default=2000, help="redonda truco: deals per signature"
    )
    parser.add_argument(
        "--envido-deals", type=int, default=100000, help="redonda envido: deals per tanto"
    )
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--skip-envido", action="store_true")
    parser.add_argument("--skip-truco", action="store_true")
    args = parser.parse_args()
    formats = [Format(f) for f in args.format or FORMATS]
    policies = [CardOrder(p) for p in args.policy or CardOrder]

    for fmt in formats:
        if not args.skip_envido:
            start = time.perf_counter()
            rows = envido_rows(fmt, args.envido_deals, args.seed)
            store(rows, fmt, "envido", None)
            print(f"{fmt} envido: {len(rows)} rows ({time.perf_counter() - start:.1f}s)")
        if not args.skip_truco:
            for order in policies:
                start = time.perf_counter()
                rows = truco_rows(fmt, order, args.deals, args.seed)
                store(rows, fmt, "truco", order.value)
                elapsed = time.perf_counter() - start
                print(f"{fmt} truco/{order}: {len(rows)} rows ({elapsed:.1f}s)")


if __name__ == "__main__":
    main()
