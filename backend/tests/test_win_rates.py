"""experiments/win_rates.py: hand strength by tanto (envido) and truco ranks, pica-pica (exact)
and redonda (Monte Carlo), both checked against the engine."""

import random

import pytest
from experiments import win_rates as w
from sqlmodel import Session, select

from app.bots.settings import CardOrder
from app.db import get_engine
from app.models import WinRate
from app.truco.cards import Card, Suit
from app.truco.config import Format
from app.truco.envido import said_in_order, tanto
from app.truco.hand import Action, Contest
from app.truco.table import team_of

E, B, OR, C = Suit.ESPADA, Suit.BASTO, Suit.ORO, Suit.COPA
DETERMINISTIC = [o for o in CardOrder if o != CardOrder.RANDOM]


# --- envido -------------------------------------------------------------------------------


def test_envido_counts_match_brute_force():
    counts = w.envido_counts()
    for index in random.Random(1).sample(range(len(w.HANDS)), 5):
        hand = set(w.HANDS[index])
        rivals = [h for h in w.HANDS if not hand & set(h)]
        own, by_tanto = counts[index]
        assert own == tanto(w.cards_of(hand))
        assert sum(by_tanto.values()) == len(rivals) == 7770
        for t, n in by_tanto.items():
            assert n == sum(1 for h in rivals if tanto(w.cards_of(h)) == t)


def test_pica_pica_envido_by_tanto():
    """Every hand once per seat; 11.6: the mano wins an equal tanto, the pie loses it."""
    rows = w.pica_pica_envido()
    assert sorted(rows) == [*range(8), *range(20, 34)]
    assert sum(r.seats[0].samples for r in rows.values()) == len(w.HANDS) * 7770
    for row in rows.values():
        assert row.exact and row.seats[0].wins > row.seats[1].wins
    assert rows[33].by_seat[0] == 1 and rows[0].by_seat[1] == 0
    by_strength = sorted(rows, key=lambda t: rows[t].strength)
    assert by_strength == sorted(rows)


@pytest.mark.parametrize("seed", range(20))
def test_envido_winner_is_the_engines(seed):
    """11.4-11.6: the team the table's declarations find is the best tanto's, ties going to
    the one nearer the mano (the engine may credit a partner who stayed quiet behind it)."""
    rng = random.Random(seed)
    tantos = [rng.choice([20, 25, 27, 27, 33, 5]) for _ in range(6)]
    _, winner = said_in_order(range(6), dict(enumerate(tantos)))
    assert team_of(w.envido_winner(tantos)) == team_of(winner)


def test_redonda_envido():
    rows = w.redonda_envido(300, seed=1)
    assert sorted(rows) == [*range(8), *range(20, 34)]
    for row in rows.values():
        assert not row.exact and len(row.seats) == 6
        assert all(t.samples == 300 for t in row.seats)
    # 33 only loses to another 33 nearer the mano: never as mano, rarely elsewhere.
    assert rows[33].by_seat[0] == 1 and min(rows[33].by_seat) > 0.9
    assert rows[0].strength < 0.5 < rows[30].strength
    assert w.redonda_envido(300, seed=1)[27].by_seat == rows[27].by_seat  # seeded


# --- truco: pica-pica (exact) ------------------------------------------------------------


def only(outcomes):
    [(chance, actors, winner)] = outcomes
    assert chance == 1
    return actors, winner


def test_outcomes_first_two_rondas_decide():
    """7.2: two rondas won end the mano; the ronda winner leads the next one."""
    mano = [Card(1, E), Card(7, E), Card(4, C)]
    pie = [Card(3, OR), Card(2, OR), Card(5, C)]
    actors, winner = only(w.outcomes(mano, pie, CardOrder.STRONGEST_FIRST))
    assert (actors, winner) == ([w.MANO, w.PIE, w.MANO, w.PIE], w.MANO)


def test_outcomes_parda_then_the_mano_leads():
    """7.6: after a parda the mano starts the next ronda; two pardas leave it to the third."""
    mano = [Card(3, OR), Card(1, B), Card(4, C)]
    pie = [Card(3, C), Card(1, E), Card(4, OR)]
    actors, winner = only(w.outcomes(mano, pie, CardOrder.WEAKEST_FIRST))
    # 4c vs 4o: parda; 3o vs 3c: parda; 1b vs 1e: pie.
    assert (actors, winner) == ([w.MANO, w.PIE] * 3, w.PIE)


def test_outcomes_random_branches_over_every_card():
    mano = [Card(1, E), Card(7, E), Card(4, C)]
    pie = [Card(3, OR), Card(2, OR), Card(5, C)]
    out = w.outcomes(mano, pie, CardOrder.RANDOM)
    assert sum(chance for chance, _, _ in out) == pytest.approx(1)
    # 1e and 7e beat every card of the pie: the mano wins two rondas in any order.
    assert {winner for _, _, winner in out} == {w.MANO}


@pytest.mark.parametrize("order", [CardOrder.CHEAPEST_WINNER, CardOrder.RANDOM])
def test_pica_pica_truco_matches_brute_force(order):
    """Signatures and rival counts give what playing every rival hand of one hand gives."""
    mine = w.cards_of(w.HANDS[1234])
    sig = w.signature(mine)
    expected = [[0.0, 0.0], [0.0, 0.0]]
    for rival in w.HANDS:
        if set(rival) & set(w.HANDS[1234]):
            continue
        for seat in (w.MANO, w.PIE):
            deal = (mine, w.cards_of(rival)) if seat == w.MANO else (w.cards_of(rival), mine)
            for chance, _, winner in w.outcomes(*deal, order):
                expected[seat][0] += chance * (winner == seat)
                expected[seat][1] += chance
    got = w.pica_pica_truco(order, only={sig})[sig]
    for tally, (wins, samples) in zip(got.seats, expected, strict=True):
        assert tally.wins == pytest.approx(wins)
        assert tally.samples == pytest.approx(samples) == pytest.approx(7770)


# --- truco: redonda (Monte Carlo) --------------------------------------------------------


def engine_winner(hands, order):
    """Play a strict redonda mano in the engine, every seat on `order`, nothing sung."""
    contest = Contest(range(6), dict(enumerate(hands)), pica_pica=False)
    while not contest.finished:
        seat = contest.to_act
        table = [card for _, card in contest.rounds[-1]]
        card = w.choose_card(contest.hands[seat], table, order, None)
        contest.apply(Action.play(card), seat)
    return contest.winner


@pytest.mark.parametrize("order", DETERMINISTIC)
def test_play_out_is_the_engines_redonda(order):
    """7.1-7.3, 7.6 in three a side: the same winner as the engine's Contest, deal by deal."""
    rng = random.Random(7)
    for _ in range(200):
        deck = rng.sample(w.DECK, 18)
        hands = [deck[i : i + 3] for i in range(0, 18, 3)]
        assert w.play_out(hands, order, rng) == engine_winner(hands, order)


def test_play_out_partners_tie_for_their_team():
    """7.3: two partners on the top card win the ronda; 7.6: parda then the mano's team."""
    hands = [
        [Card(3, E), Card(4, E), Card(4, B)],  # mano, team 0
        [Card(2, E), Card(5, E), Card(5, B)],
        [Card(3, B), Card(6, E), Card(6, B)],  # partner of the mano: ties the 3
        [Card(2, B), Card(10, E), Card(10, B)],
        [Card(12, E), Card(11, E), Card(11, B)],
        [Card(1, OR), Card(12, B), Card(12, OR)],
    ]
    # Strongest first: 3e and 3b (both team 0) top ronda 1, and 3e (first played) leads.
    assert w.play_out(hands, CardOrder.STRONGEST_FIRST, None) == engine_winner(
        hands, CardOrder.STRONGEST_FIRST
    )
    hands[3] = [Card(3, OR), Card(10, E), Card(10, B)]  # a rival ties the 3: parda
    assert w.play_out(hands, CardOrder.STRONGEST_FIRST, None) == engine_winner(
        hands, CardOrder.STRONGEST_FIRST
    )


def test_redonda_truco():
    best = (12, 13, 14)  # 1e, 1b, 7e
    worst = (1, 1, 1)  # three 4s
    rows = w.redonda_truco(CardOrder.STRONGEST_FIRST, 200, seed=1, only={best, worst})
    assert rows[best].by_seat == [1] * 6  # wins the first two rondas at any seat
    assert rows[worst].strength < 0.5
    assert all(t.samples == 200 for t in rows[worst].seats)
    again = w.redonda_truco(CardOrder.STRONGEST_FIRST, 200, seed=1, only={worst})
    assert again[worst].by_seat == rows[worst].by_seat  # seeded


# --- rows ---------------------------------------------------------------------------------


def strength(*rates):
    return w.Strength([w.Tally(r, 1) for r in rates])


def test_row_compresses_to_a_key_and_seats():
    r = w.row(Format.REDONDA, "truco", "random", strength(0.5, 0.25), ranks=(1, 14, 10))
    assert r["ranks"] == "14-10-1" and r["tanto"] is None
    assert r["strength"] == 0.375 and r["by_seat"] == [0.5, 0.25]


def test_store_replaces_only_its_experiment(data_dir):
    s = strength(0.75, 0.25)
    w.store(
        [w.row(Format.PICA_PICA, "envido", None, s, tanto=27)], Format.PICA_PICA, "envido", None
    )
    w.store([w.row(Format.REDONDA, "envido", None, s, tanto=27)], Format.REDONDA, "envido", None)
    w.store(
        [w.row(Format.PICA_PICA, "truco", "random", s, ranks=(1, 2, 3))],
        Format.PICA_PICA,
        "truco",
        "random",
    )
    w.store(
        [w.row(Format.PICA_PICA, "envido", None, s, tanto=30)], Format.PICA_PICA, "envido", None
    )
    with Session(get_engine()) as session:
        rows = session.exec(select(WinRate).order_by(WinRate.id)).all()
    assert [(r.format, r.canto, r.tanto, r.ranks) for r in rows] == [
        ("redonda", "envido", 27, None),
        ("pica_pica", "truco", None, "3-2-1"),
        ("pica_pica", "envido", 30, None),
    ]
    assert rows[0].by_seat == [0.75, 0.25] and rows[0].strength == 0.5
