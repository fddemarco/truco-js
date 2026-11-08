"""Physical seating: three per side, alternating teams, play moving around the table (1.2, 3.5)."""

from app.truco.table import across, facing, right_of, seats_across, side, team_of


def test_three_per_side_with_alternating_teams():
    assert [side(s) for s in range(6)] == [0, 0, 0, 1, 1, 1]
    for s in range(6):
        assert team_of(right_of(s)) != team_of(s)  # neighbours in turn order are rivals


def test_play_moves_around_the_table():
    # The last seat of a side is next to the first one of the other side, at the same end.
    assert right_of(2) == 3 and across(2) == 3
    assert right_of(5) == 0 and across(5) == 0


def test_seats_across_from_the_viewers_left_to_right():
    assert seats_across(0) == [5, 4, 3]
    assert seats_across(1) == [5, 4, 3]
    assert seats_across(4) == [2, 1, 0]


def test_pica_pica_rivals_are_across_or_diagonal():
    # Same numbers face each other (3.5): straight across for the #2s, diagonal otherwise.
    assert facing(1) == across(1) == 4
    assert facing(0) == 3 and across(0) == 5
    for s in range(6):
        assert facing(s) in seats_across(s)  # always on the other side, so visible
