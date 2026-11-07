"""Seats, teams, numbering and turn order (3.4, 3.5, 5.2, 5.5, 15.4).

Seats are 0..5 and play moves to the right, which is seat + 1. Teams alternate:
team 0 sits at even seats and team 1 at odd seats. Players with the same reserved number
face each other: team 0 number k sits at seat 2(k-1) and team 1 number k at the facing seat.
"""

import random

from app.truco.cards import shuffled_deck

SEATS = 6
TEAMS = (0, 1)


def team_of(seat: int) -> int:
    return seat % 2


def other(team: int) -> int:
    return 1 - team


def right_of(seat: int) -> int:
    return (seat + 1) % SEATS


def facing(seat: int) -> int:
    return (seat + 3) % SEATS


def number_of(seat: int) -> int:
    """Reserved number 1-2-3 of the player at `seat`."""
    return (seat if team_of(seat) == 0 else facing(seat)) // 2 + 1


def seat_of(team: int, number: int) -> int:
    seat = 2 * (number - 1)
    return seat if team == 0 else facing(seat)


def order_from(start: int) -> list[int]:
    return [(start + i) % SEATS for i in range(SEATS)]


def mano_of(dealer: int) -> int:
    """The player to the dealer's right is mano (2, 5.5)."""
    return right_of(dealer)


def duel_order(mano: int) -> list[tuple[int, int]]:
    """Pica-pica duels in play order, each as (duel mano, rival) (15.4)."""
    return [((mano + i) % SEATS, facing((mano + i) % SEATS)) for i in range(3)]


def choose_first_dealer(rng: random.Random) -> int:
    """Each player draws a card, the highest truco card deals; tied players redraw (5.2)."""
    contenders = list(range(SEATS))
    while True:
        deck = shuffled_deck(rng)
        draws = {seat: deck[i].rank for i, seat in enumerate(contenders)}
        best = max(draws.values())
        contenders = [s for s in contenders if draws[s] == best]
        if len(contenders) == 1:
            return contenders[0]
