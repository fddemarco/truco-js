import random

from app.truco.match import ResultKind
from app.truco.standings import MatchRecord, standings

D = ResultKind.DEPORTIVO


def sporting(a: str, b: str, score_a: int, score_b: int) -> MatchRecord:
    return MatchRecord(a, b, D, a if score_a > score_b else b, score_a, score_b)


def names(rows) -> list[str]:
    return [r.team for r in rows]


def test_ordered_by_wins_then_difference():
    rows = standings(
        ["A", "B", "C"],
        [sporting("A", "B", 30, 20), sporting("A", "C", 30, 25), sporting("B", "C", 30, 10)],
    )
    assert names(rows) == ["A", "B", "C"]
    a = rows[0]
    assert (a.played, a.won, a.points_for, a.points_against, a.diff) == (2, 2, 60, 45, 15)


def test_points_for_break_equal_wins_and_difference():
    rows = standings(["A", "B", "C", "D"], [sporting("A", "C", 30, 20), sporting("B", "D", 20, 10)])
    # A and B: 1 win, +10 each; A scored more.
    assert names(rows)[:2] == ["A", "B"]


def test_administrative_win_counts_30_and_average_difference():
    rows = standings(
        ["A", "B", "C", "D"],
        [
            sporting("A", "C", 30, 20),
            sporting("A", "D", 30, 10),
            MatchRecord("A", "B", ResultKind.AUSENCIA, "A"),
        ],
    )
    a = next(r for r in rows if r.team == "A")
    assert (a.won, a.points_for, a.diff) == (3, 90, 10 + 20 + 15)
    b = next(r for r in rows if r.team == "B")
    assert (b.lost, b.points_for, b.diff) == (1, 0, 0)


def test_administrative_win_without_sporting_wins_has_zero_difference():
    rows = standings(["A", "B"], [MatchRecord("A", "B", ResultKind.SANCION, "B")])
    b = rows[0]
    assert (b.team, b.won, b.points_for, b.diff) == ("B", 1, 30, 0)


def test_double_disqualification_has_no_winner():
    rows = standings(["A", "B"], [MatchRecord("A", "B", ResultKind.DOBLE_DESCALIFICACION, None)])
    assert all(r.won == 0 and r.played == 1 for r in rows)


def test_head_to_head_breaks_the_tie():
    rows = standings(
        ["A", "B", "C", "D"],
        [
            sporting("B", "A", 20, 30),  # A beats B
            sporting("A", "C", 20, 30),
            sporting("B", "D", 30, 20),
        ],
    )
    # A and B: 1 win, diff 0, 50 points each; A won the direct match.
    assert names(rows) == ["C", "A", "B", "D"]
    assert not any(r.drawn_lots for r in rows)


def test_unresolved_tie_goes_to_a_draw():
    matches = [sporting("A", "B", 30, 20), sporting("B", "C", 30, 20), sporting("C", "A", 30, 20)]
    rows = standings(["A", "B", "C"], matches, random.Random(3))
    assert all(r.drawn_lots for r in rows)
    assert sorted(names(rows)) == ["A", "B", "C"]
