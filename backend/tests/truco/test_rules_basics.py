import random

import pytest

from app.truco.cards import Card, Suit, new_deck
from app.truco.envido import EnvidoCall, can_call, envido_points, said_in_order, tanto
from app.truco.rounds import hand_winner, round_winner
from app.truco.score import capped
from app.truco.table import (
    choose_first_dealer,
    duel_order,
    facing,
    mano_of,
    number_of,
    team_of,
)

E, R, F = EnvidoCall.ENVIDO, EnvidoCall.REAL_ENVIDO, EnvidoCall.FALTA_ENVIDO


def c(number: int, suit: str) -> Card:
    return Card(number, Suit(suit))


# --- cards (5.1, Anexo A) ------------------------------------------------------------


def test_deck_has_40_cards_without_8_or_9():
    deck = new_deck()
    assert len(deck) == len(set(deck)) == 40
    assert not {card.number for card in deck} & {8, 9}


def test_invalid_card_rejected():
    with pytest.raises(ValueError):
        Card(8, Suit.ORO)


def test_hierarchy_order():
    ordered = [
        c(1, "espada"),
        c(1, "basto"),
        c(7, "espada"),
        c(7, "oro"),
        c(3, "copa"),
        c(2, "oro"),
        c(1, "oro"),
        c(12, "basto"),
        c(11, "basto"),
        c(10, "basto"),
        c(7, "copa"),
        c(6, "oro"),
        c(5, "oro"),
        c(4, "oro"),
    ]
    ranks = [card.rank for card in ordered]
    assert ranks == sorted(ranks, reverse=True)
    assert len(set(ranks)) == len(ranks)


@pytest.mark.parametrize(
    "a,b",
    [
        (c(3, "oro"), c(3, "espada")),
        (c(1, "oro"), c(1, "copa")),
        (c(7, "copa"), c(7, "basto")),
        (c(12, "oro"), c(12, "copa")),
    ],
)
def test_same_group_cards_tie(a, b):
    assert a.rank == b.rank


# --- envido (11.1, Anexo B) ------------------------------------------------------------


@pytest.mark.parametrize(
    "cards,expected",
    [
        ([c(7, "oro"), c(6, "oro"), c(1, "espada")], 33),
        ([c(10, "oro"), c(12, "oro"), c(1, "espada")], 20),
        ([c(7, "oro"), c(6, "copa"), c(1, "espada")], 7),
        ([c(10, "oro"), c(11, "copa"), c(12, "espada")], 0),
        ([c(7, "oro"), c(6, "oro"), c(5, "oro")], 33),  # no flor: best two count
        ([c(3, "oro"), c(12, "oro"), c(7, "copa")], 23),
    ],
)
def test_tanto(cards, expected):
    assert tanto(cards) == expected


@pytest.mark.parametrize(
    "calls,ok",
    [
        ((E,), True),
        ((E, E), True),
        ((E, E, E), False),
        ((R, E), False),
        ((F, R), False),
        ((E, E, R, F), True),
        ((R, R), False),
    ],
)
def test_valid_sequences(calls, ok):
    assert can_call(calls[:-1], calls[-1]) is ok


@pytest.mark.parametrize(
    "calls,querido,no_querido",
    [
        ((E,), 2, 1),
        ((R,), 3, 1),
        ((F,), None, 1),
        ((E, E), 4, 2),
        ((E, R), 5, 2),
        ((E, F), None, 2),
        ((R, F), None, 3),
        ((E, E, F), None, 4),
        ((E, E, R), 7, 4),
        ((E, R, F), None, 5),
        ((E, E, R, F), None, 7),
    ],
)
def test_envido_points_table(calls, querido, no_querido):
    kw = {"pica_pica": False, "scores": (0, 0), "winner": 0}
    assert envido_points(calls, False, **kw) == no_querido
    if querido is not None:
        assert envido_points(calls, True, **kw) == querido


def test_falta_envido_both_in_malas_decides_the_partido():
    assert envido_points([F], True, pica_pica=False, scores=(15, 3), winner=1) == 27


def test_falta_envido_with_buenas_is_what_the_leader_needs():
    assert envido_points([F], True, pica_pica=False, scores=(20, 3), winner=1) == 10
    assert envido_points([E, F], True, pica_pica=False, scores=(4, 16), winner=0) == 14


def test_falta_envido_in_pica_pica_is_six():
    assert envido_points([E, E, R, F], True, pica_pica=True, scores=(20, 3), winner=1) == 6


# --- truco (12.2) and score (1.4, 1.5) ---------------------------------------------------


def test_score_is_capped_at_30():
    assert capped(28, 4) == 30


# --- rondas and pardas (7.2, 7.3, 7.6) ---------------------------------------------------


def test_round_winner_highest_card():
    plays = [(0, c(4, "oro")), (1, c(1, "espada")), (2, c(3, "oro"))]
    assert round_winner(plays, team_of) == (1, 1)


def test_round_tie_between_teammates_goes_to_first_who_played():
    plays = [(0, c(3, "oro")), (1, c(2, "oro")), (2, c(3, "copa")), (3, c(4, "oro"))]
    assert round_winner(plays, team_of) == (0, 0)


def test_round_tie_between_rivals_is_parda():
    plays = [(0, c(3, "oro")), (1, c(3, "copa"))]
    assert round_winner(plays, team_of)[0] is None


P = None


@pytest.mark.parametrize(
    "results,expected",
    [
        ([P, 0], 0),
        ([P, P, 1], 1),
        ([P, P, P], "mano"),
        ([1, P], 1),
        ([0, 1, P], 0),
        ([0, 1, 1], 1),
        ([1, 1], 1),
        ([0], None),
        ([0, 1], None),
        ([P, P], None),
    ],
)
def test_pardas_table(results, expected):
    mano_team = 1
    assert hand_winner(results, mano_team) == (mano_team if expected == "mano" else expected)


# --- table (3.4, 3.5, 5.2, 15.4) -------------------------------------------------------


def test_same_numbers_face_each_other_and_teams_alternate():
    for seat in range(6):
        assert number_of(facing(seat)) == number_of(seat)
        assert team_of(facing(seat)) != team_of(seat)
        assert team_of((seat + 1) % 6) != team_of(seat)
    assert sorted((team_of(s), number_of(s)) for s in range(6)) == [
        (t, n) for t in (0, 1) for n in (1, 2, 3)
    ]


def test_mano_is_right_of_dealer():
    assert mano_of(5) == 0
    assert mano_of(2) == 3


def test_duel_order_follows_the_table_from_mano():
    assert duel_order(4) == [(4, 1), (5, 2), (0, 3)]
    for a, b in duel_order(4):
        assert number_of(a) == number_of(b)


def test_first_dealer_is_a_seat():
    assert all(0 <= choose_first_dealer(random.Random(seed)) < 6 for seed in range(20))


# --- what the table hears of a strict envido (11.4–11.6) --------------------------------


def test_said_in_order_rivals_declare_only_to_beat_and_teammates_of_the_best_stay_silent():
    said, best = said_in_order([0, 1, 2, 3, 4, 5], {0: 4, 1: 31, 2: 24, 3: 31, 4: 25, 5: 31})
    assert said == {0: 4, 1: 31, 2: None, 4: None}  # 3 and 5 never reveal their 31
    assert best == 1


def test_said_in_order_a_silent_player_speaks_once_their_team_is_behind():
    # Seat 2 (33) stays silent while seat 0 leads with 20; seat 3 then leads with 25, so when
    # the turn comes round seat 2 declares and wins.
    said, best = said_in_order([0, 1, 2, 3, 4, 5], {0: 20, 1: 10, 2: 33, 3: 25, 4: 5, 5: 7})
    assert best == 2 and said[2] == 33
    assert said[1] is None and said[4] is None


def test_said_in_order_a_tie_goes_to_whoever_is_closer_to_mano():
    # 11.6: seat 2 (31) was silent; seat 3 says 31 later in the order. Seat 2 is closer to
    # mano, so their 31 beats it when they speak.
    said, best = said_in_order([0, 1, 2, 3], {0: 20, 1: 4, 2: 31, 3: 31})
    assert best == 2 and said == {0: 20, 1: None, 3: 31, 2: 31}
