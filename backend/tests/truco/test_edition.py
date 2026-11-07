import random
from itertools import combinations

import pytest

from app.truco.config import GameConfig, RuleMode
from app.truco.edition import (
    Edition,
    GroupStage,
    Knockout,
    WarningLedger,
    draw_groups,
    group_qualifiers,
    next_round,
    pair_winner,
    round_robin,
    seed_bracket,
)
from app.truco.match import MatchResult, ResultKind
from app.truco.standings import Standing

D = ResultKind.DEPORTIVO


def win(winner: int) -> MatchResult:
    return MatchResult(D, winner, (30, 20) if winner == 0 else (20, 30))


def row(team: str, won: int, diff: float = 0, points_for: float = 0) -> Standing:
    return Standing(team, won=won, diff=diff, points_for=points_for)


# --- edition --------------------------------------------------------------------------


def test_edition_carries_the_rule_mode():
    e = Edition(
        "2026",
        (GroupStage("Clasificatoria", groups=2), Knockout("Televisada")),
        config=GameConfig(mode=RuleMode.INTERACTIVE),
    )
    assert e.config.interactive


def test_knockout_must_be_the_last_phase():
    with pytest.raises(ValueError, match="last phase"):
        Edition("x", (Knockout("Cuartos"), GroupStage("Grupos", groups=2)))
    with pytest.raises(ValueError):
        Edition("x", ())


def test_invalid_group_stage():
    with pytest.raises(ValueError):
        GroupStage("G", groups=2, best_extra=2)
    with pytest.raises(ValueError):
        GroupStage("G", groups=0)


def test_invited_teams_join_their_phase():
    e = Edition("x", (GroupStage("G", groups=2), Knockout("K", invited=("Invitado",))))
    assert e.entrants(1, ["A", "B", "C"]) == ["A", "B", "C", "Invitado"]
    assert e.entrants(1, ["Invitado", "A"]) == ["Invitado", "A"]  # no duplicates


# --- groups ----------------------------------------------------------------------------


def test_serpentine_draw_spreads_the_seeds():
    groups = draw_groups([f"T{i}" for i in range(1, 9)], 3)
    assert groups == [["T1", "T6", "T7"], ["T2", "T5", "T8"], ["T3", "T4"]]


def test_draw_needs_two_teams_per_group():
    with pytest.raises(ValueError):
        draw_groups(["A", "B", "C"], 2)


@pytest.mark.parametrize("n", [4, 5, 6])
def test_round_robin_everyone_meets_once(n):
    teams = [f"T{i}" for i in range(n)]
    fechas = round_robin(teams)
    played = [frozenset(p) for fecha in fechas for p in fecha]
    assert sorted(played, key=sorted) == sorted(
        (frozenset(c) for c in combinations(teams, 2)), key=sorted
    )
    for fecha in fechas:
        teams_in_fecha = [t for pair in fecha for t in pair]
        assert len(teams_in_fecha) == len(set(teams_in_fecha))


def test_group_qualifiers_in_seeding_order_with_best_thirds():
    stage = GroupStage("G", groups=3, qualify_per_group=2, best_extra=1)
    tables = [
        [row("A1", 3, 20), row("A2", 2, 5), row("A3", 1, -5)],
        [row("B1", 3, 30), row("B2", 2, 10), row("B3", 1, 2)],
        [row("C1", 2, 15), row("C2", 1, 0), row("C3", 0, -10)],
    ]
    assert group_qualifiers(stage, tables) == ["B1", "A1", "C1", "B2", "A2", "C2", "B3"]


def test_ties_across_groups_go_to_a_draw():
    stage = GroupStage("G", groups=2, qualify_per_group=1)
    tables = [[row("A1", 2, 10, 60)], [row("B1", 2, 10, 60)]]
    orders = {tuple(group_qualifiers(stage, tables, random.Random(s))) for s in range(20)}
    assert orders == {("A1", "B1"), ("B1", "A1")}


def test_group_count_must_match():
    with pytest.raises(ValueError):
        group_qualifiers(GroupStage("G", groups=2), [[row("A", 1)]])


# --- knockout --------------------------------------------------------------------------


def test_bracket_seeds_meet_as_late_as_possible():
    pairs = seed_bracket([f"S{i}" for i in range(1, 9)])
    assert pairs == [("S1", "S8"), ("S4", "S5"), ("S2", "S7"), ("S3", "S6")]


def test_top_seeds_get_the_byes():
    pairs = seed_bracket(["S1", "S2", "S3", "S4", "S5", "S6"])
    assert ("S1", None) in pairs and ("S2", None) in pairs
    assert len(pairs) == 4


def test_next_round_pairs_winners_and_passes_byes():
    pairs = seed_bracket(["S1", "S2", "S3", "S4", "S5", "S6"])
    # (S1, bye), (S4, S5), (S2, bye), (S3, S6)
    semis = next_round(pairs, [None, win(1), None, win(0)])
    assert semis == [("S1", "S5"), ("S2", "S3")]
    final = next_round(semis, [win(0), win(1)])
    assert final == [("S1", "S3")]
    with pytest.raises(ValueError):
        next_round(final, [win(0)])


def test_double_disqualification_sends_nobody_through():
    double = MatchResult(ResultKind.DOBLE_DESCALIFICACION, None, (12, 9))
    assert pair_winner(("A", "B"), double) is None
    nxt = next_round([("A", "B"), ("C", "D")], [double, win(0)])
    assert nxt == [(None, "C")]  # C advances on a bye
    assert pair_winner(nxt[0], None) == "C"


def test_administrative_results_count_like_any_win():
    absence = MatchResult(ResultKind.AUSENCIA, 1, (0, 0))
    assert pair_winner(("A", "B"), absence) == "B"


def test_missing_result_is_an_error():
    with pytest.raises(ValueError):
        pair_winner(("A", "B"), None)


# --- warnings across partidos (19.2) -----------------------------------------------------


def test_warnings_accumulate_to_disqualification():
    e = Edition("x", (GroupStage("G", groups=2), Knockout("K")), warnings_to_disqualify=3)
    ledger = WarningLedger(e)
    assert not ledger.add("A", 0, 2)
    assert ledger.add("A", 1, 1)


def test_a_phase_can_reset_the_count():
    e = Edition(
        "x",
        (GroupStage("Clasificatoria", groups=2), Knockout("Televisada", resets_warnings=True)),
        warnings_to_disqualify=3,
    )
    ledger = WarningLedger(e)
    ledger.add("A", 0, 2)
    assert ledger.count("A", 1) == 0
    assert not ledger.add("A", 1, 2)
    assert ledger.count("A", 0) == 2


def test_no_accumulation_unless_configured():
    ledger = WarningLedger(Edition("x", (Knockout("K"),)))
    assert not ledger.add("A", 0, 10)
