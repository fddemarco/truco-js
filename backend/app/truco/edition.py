"""Edition configuration: the Condiciones Particulares of a tournament (1.8, 1.13, 19.2).

An `Edition` fixes the rule mode for every partido and a sequence of phases. Group stages
play a round robin per group and qualify the top places of each group plus, optionally, the
best of the next place across groups. A knockout is a single-elimination bracket and must be
the last phase. Invited teams enter directly at the phase that names them.

Disciplinary warnings can accumulate across partidos up to a disqualification threshold,
and a phase can reset the count (e.g. between the qualifying and the televised stage).
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import groupby

from app.truco.config import GameConfig
from app.truco.match import MatchResult
from app.truco.standings import Standing


@dataclass(frozen=True)
class GroupStage:
    name: str
    groups: int
    qualify_per_group: int = 2
    best_extra: int = 0  # best teams of the next place across groups, e.g. best thirds
    invited: tuple[str, ...] = ()
    resets_warnings: bool = False

    def __post_init__(self) -> None:
        if self.groups < 1 or self.qualify_per_group < 1 or self.best_extra < 0:
            raise ValueError(f"{self.name}: invalid group stage")
        if self.best_extra >= self.groups:
            raise ValueError(f"{self.name}: best_extra must be fewer than the groups")


@dataclass(frozen=True)
class Knockout:
    name: str
    invited: tuple[str, ...] = ()
    resets_warnings: bool = False


Phase = GroupStage | Knockout


@dataclass(frozen=True)
class Edition:
    name: str
    phases: tuple[Phase, ...]
    config: GameConfig = field(default_factory=GameConfig)
    warnings_to_disqualify: int | None = None  # across partidos; None = no accumulation

    def __post_init__(self) -> None:
        if not self.phases:
            raise ValueError("an edition needs at least one phase")
        if any(isinstance(p, Knockout) for p in self.phases[:-1]):
            raise ValueError("a knockout decides the champion, so it must be the last phase")
        if self.warnings_to_disqualify is not None and self.warnings_to_disqualify < 1:
            raise ValueError("warnings_to_disqualify must be positive")

    def entrants(self, phase: int, qualified: Sequence[str]) -> list[str]:
        """Teams playing `phase`: those qualified from the previous one plus its invited teams."""
        invited = [t for t in self.phases[phase].invited if t not in qualified]
        return [*qualified, *invited]


# --- group stage ----------------------------------------------------------------------


def draw_groups(seeded: Sequence[str], groups: int) -> list[list[str]]:
    """Serpentine draw by seeding order: 1→A, 2→B, …, then back from the last group."""
    if len(set(seeded)) != len(seeded):
        raise ValueError("duplicate teams")
    if len(seeded) < 2 * groups:
        raise ValueError("every group needs at least two teams")
    result: list[list[str]] = [[] for _ in range(groups)]
    for i, team in enumerate(seeded):
        lap, pos = divmod(i, groups)
        result[pos if lap % 2 == 0 else groups - 1 - pos].append(team)
    return result


def round_robin(teams: Sequence[str]) -> list[list[tuple[str, str]]]:
    """Fixtures by fecha (circle method): everyone meets once, nobody plays twice a fecha."""
    slots: list[str | None] = list(teams)
    if len(slots) % 2:
        slots.append(None)  # bye
    n = len(slots)
    fechas = []
    for _ in range(n - 1):
        pairs = [(slots[i], slots[n - 1 - i]) for i in range(n // 2)]
        fechas.append([(a, b) for a, b in pairs if a is not None and b is not None])
        slots = [slots[0], slots[-1], *slots[1:-1]]
    return fechas


def rank_across_groups(rows: Sequence[Standing], rng: random.Random) -> list[Standing]:
    """Compare teams of different groups with 1.13; they never met, so ties go to a draw."""

    def key(s: Standing) -> tuple[float, ...]:
        return (s.won, s.diff, s.points_for)

    ranked: list[Standing] = []
    for _, group in groupby(sorted(rows, key=key, reverse=True), key=key):
        tied = list(group)
        rng.shuffle(tied)
        ranked += tied
    return ranked


def group_qualifiers(
    stage: GroupStage, tables: Sequence[Sequence[Standing]], rng: random.Random | None = None
) -> list[str]:
    """Qualified teams in seeding order: the best group winners first, then runners-up, …

    `tables` are each group's final standings (see `standings.standings`).
    """
    rng = rng or random.Random()
    if len(tables) != stage.groups:
        raise ValueError(f"{stage.name}: expected {stage.groups} groups")
    seeds: list[str] = []
    for place in range(stage.qualify_per_group):
        rows = [table[place] for table in tables if len(table) > place]
        seeds += [s.team for s in rank_across_groups(rows, rng)]
    if stage.best_extra:
        place = stage.qualify_per_group
        rows = [table[place] for table in tables if len(table) > place]
        seeds += [s.team for s in rank_across_groups(rows, rng)[: stage.best_extra]]
    return seeds


# --- knockout ---------------------------------------------------------------------------

Pair = tuple[str | None, str | None]  # None = bye


def _seed_order(size: int) -> list[int]:
    """Bracket positions of seeds 1..size so the top seeds meet as late as possible."""
    order = [1]
    while len(order) < size:
        n = len(order) * 2
        order = [x for s in order for x in (s, n + 1 - s)]
    return order


def seed_bracket(seeds: Sequence[str]) -> list[Pair]:
    """First round, 1 vs N, 2 vs N-1, … Top seeds get the byes when N isn't a power of 2."""
    if len(seeds) < 2:
        raise ValueError("a knockout needs at least two teams")
    size = 1
    while size < len(seeds):
        size *= 2
    slots = [seeds[s - 1] if s <= len(seeds) else None for s in _seed_order(size)]
    return [(slots[i], slots[i + 1]) for i in range(0, size, 2)]


def pair_winner(pair: Pair, result: MatchResult | None) -> str | None:
    """Who goes through. A bye passes the present team; doble descalificación passes nobody."""
    a, b = pair
    if a is None or b is None:
        return a or b
    if result is None:
        raise ValueError(f"{a} vs {b} has no result")
    if result.winner is None:
        return None
    return (a, b)[result.winner]  # team 0 = first of the pair


def next_round(pairs: Sequence[Pair], results: Sequence[MatchResult | None]) -> list[Pair]:
    """Pair the winners of consecutive matches. `results[i]` is the result of `pairs[i]`."""
    if len(pairs) != len(results):
        raise ValueError("one result per pair")
    if len(pairs) < 2:
        raise ValueError("the final has no next round")
    winners = [pair_winner(p, r) for p, r in zip(pairs, results, strict=True)]
    return [(winners[i], winners[i + 1]) for i in range(0, len(winners), 2)]


# --- disciplinary accumulation (19.2) ----------------------------------------------------


class WarningLedger:
    """Disciplinary warnings across partidos, as the edition's Condiciones Particulares set."""

    def __init__(self, edition: Edition) -> None:
        self.edition = edition
        self._counts: dict[tuple[str, int], int] = {}

    def _segment(self, phase: int) -> int:
        """The phase where the current count started (the last reset at or before `phase`)."""
        return max(
            (i for i in range(phase + 1) if self.edition.phases[i].resets_warnings), default=0
        )

    def count(self, team: str, phase: int) -> int:
        return self._counts.get((team, self._segment(phase)), 0)

    def add(self, team: str, phase: int, warnings: int = 1) -> bool:
        """Record a partido's warnings. Returns True if the team is now disqualified."""
        key = (team, self._segment(phase))
        self._counts[key] = self._counts.get(key, 0) + warnings
        limit = self.edition.warnings_to_disqualify
        return limit is not None and self._counts[key] >= limit
