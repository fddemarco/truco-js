"""Ronda winners and the pardas table (7.2, 7.3, 7.6)."""

from collections.abc import Callable, Sequence

from app.truco.cards import Card

Play = tuple[int, Card]  # (seat, card)


def round_winner(plays: Sequence[Play], team_of: Callable[[int], int]) -> tuple[int | None, int]:
    """Return (winning team or None for parda, seat that starts the next ronda if not parda).

    Teammates tied on the highest card win for their team, and the first of them to play
    starts the next ronda (7.3).
    """
    best = max(card.rank for _, card in plays)
    top = [seat for seat, card in plays if card.rank == best]
    teams = {team_of(seat) for seat in top}
    if len(teams) > 1:
        return None, top[0]
    return teams.pop(), top[0]


def hand_winner(results: Sequence[int | None], mano_team: int) -> int | None:
    """Winner of the mano from ronda results (None = parda), or None if still undecided (7.6)."""
    if len(results) >= 2:
        first, second = results[0], results[1]
        if first is None and second is not None:
            return second
        if first is not None and (second is None or second == first):
            return first
    if len(results) == 3:
        first, third = results[0], results[2]
        if third is None:
            return first if first is not None else mano_team
        return third
    return None
