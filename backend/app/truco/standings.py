"""Group standings and tiebreakers (1.13, 1.14).

Phases, groups, brackets and qualification across groups are in `edition.py`.
"""

import random
from collections.abc import Sequence
from dataclasses import dataclass
from itertools import groupby

from app.truco.match import ResultKind
from app.truco.score import TARGET

ADMINISTRATIVE_POINTS = TARGET


@dataclass(frozen=True)
class MatchRecord:
    """A finished partido of the phase. Scores matter only for deportivo results."""

    team_a: str
    team_b: str
    kind: ResultKind
    winner: str | None
    score_a: int = 0
    score_b: int = 0


@dataclass
class Standing:
    team: str
    played: int = 0
    won: int = 0
    lost: int = 0
    points_for: float = 0
    points_against: float = 0
    diff: float = 0
    drawn_lots: bool = False  # position decided by the sorteo de Se Pica TSA


def standings(
    teams: Sequence[str], matches: Sequence[MatchRecord], rng: random.Random | None = None
) -> list[Standing]:
    rng = rng or random.Random()
    table = {t: Standing(t) for t in teams}

    # Average difference of each team's deportivo wins, credited for administrative wins.
    sporting_diffs: dict[str, list[int]] = {t: [] for t in teams}
    for m in matches:
        if m.kind == ResultKind.DEPORTIVO and m.winner is not None:
            loser_score, winner_score = sorted((m.score_a, m.score_b))
            sporting_diffs[m.winner].append(winner_score - loser_score)

    for m in matches:
        a, b = table[m.team_a], table[m.team_b]
        a.played += 1
        b.played += 1
        if m.winner is not None:  # doble descalificación: neither adds a win
            table[m.winner].won += 1
            table[m.team_b if m.winner == m.team_a else m.team_a].lost += 1
        if m.kind == ResultKind.DEPORTIVO:
            for row, mine, theirs in ((a, m.score_a, m.score_b), (b, m.score_b, m.score_a)):
                row.points_for += mine
                row.points_against += theirs
                row.diff += mine - theirs
        elif m.winner is not None:
            diffs = sporting_diffs[m.winner]
            avg = sum(diffs) / len(diffs) if diffs else 0
            winner = table[m.winner]
            winner.points_for += ADMINISTRATIVE_POINTS
            winner.diff += avg

    def key(s: Standing) -> tuple[float, ...]:
        return (s.won, s.diff, s.points_for)

    ordered = sorted(table.values(), key=key, reverse=True)
    result: list[Standing] = []
    for _, group in groupby(ordered, key=key):
        result += _break_tie(list(group), matches, rng)
    return result


def _break_tie(
    tied: list[Standing], matches: Sequence[MatchRecord], rng: random.Random
) -> list[Standing]:
    """Head-to-head among the tied teams, then a sorteo (1.13 criteria 4 and 5)."""
    if len(tied) == 1:
        return tied
    names = {s.team for s in tied}
    h2h = dict.fromkeys(names, 0)
    for m in matches:
        if m.team_a in names and m.team_b in names and m.winner is not None:
            h2h[m.winner] += 1
    tied.sort(key=lambda s: h2h[s.team], reverse=True)
    result: list[Standing] = []
    for _, group in groupby(tied, key=lambda s: h2h[s.team]):
        group = list(group)
        if len(group) > 1:
            rng.shuffle(group)
            for s in group:
                s.drawn_lots = True
        result += group
    return result
