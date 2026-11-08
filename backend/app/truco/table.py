"""Seats, teams, numbering and turn order (3.4, 3.5, 5.2, 5.5, 15.4).

Seats are 0..5 and play moves to the right, which is seat + 1. Teams alternate:
team 0 sits at even seats and team 1 at odd seats. Players with the same reserved number
face each other: team 0 number k sits at seat 2(k-1) and team 1 number k at the facing seat.

Physical layout: a rectangular table, three per side (1.2). Going around it, side 0 has seats
0-1-2 from left to right and side 1 continues with 3-4-5, so play moves around the table.
Directly across are 0-5, 1-4 and 2-3. The pica-pica rivals (`facing`, seat + 3) are across
for the #2s and diagonal for the #1s and #3s. A player sees the faces, and so the señas
(14.4, Anexo C), of the three players on the other side only.
"""

import random

from app.truco.cards import shuffled_deck

SEATS = 6


def team_of(seat: int) -> int:
    return seat % 2


def other(team: int) -> int:
    return 1 - team


def right_of(seat: int) -> int:
    return (seat + 1) % SEATS


def facing(seat: int) -> int:
    return (seat + 3) % SEATS


def side(seat: int) -> int:
    """Which side of the table the seat is on (0 or 1)."""
    return seat // 3


def across(seat: int) -> int:
    """The seat directly across the table."""
    return SEATS - 1 - seat


def seats_across(seat: int) -> list[int]:
    """The three seats on the other side, from the viewer's left to their right."""
    own = [3 * side(seat) + i for i in range(3)]
    return [across(s) for s in own]


def number_of(seat: int) -> int:
    """Reserved number 1-2-3 of the player at `seat`."""
    return (seat if team_of(seat) == 0 else facing(seat)) // 2 + 1


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
