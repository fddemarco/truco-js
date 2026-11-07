"""Envido: tanto calculation, valid call sequences and points (cap. 11, Anexo B)."""

from collections.abc import Sequence
from enum import StrEnum
from itertools import combinations

from app.truco.cards import Card
from app.truco.score import MALAS_MAX, TARGET

PICA_PICA_FALTA_ENVIDO = 6


class EnvidoCall(StrEnum):
    ENVIDO = "envido"
    REAL_ENVIDO = "real_envido"
    FALTA_ENVIDO = "falta_envido"


_E, _R, _F = EnvidoCall
# Anexo B.2: the only sequences allowed.
VALID_SEQUENCES = frozenset(
    {
        (_E,),
        (_R,),
        (_F,),
        (_E, _E),
        (_E, _R),
        (_E, _F),
        (_R, _F),
        (_E, _E, _F),
        (_E, _E, _R),
        (_E, _R, _F),
        (_E, _E, _R, _F),
    }
)
_VALUE = {_E: 2, _R: 3}


def tanto(cards: Sequence[Card]) -> int:
    """Envido points of a hand. No flor: with three of a suit the best two count (1.6, 11.1)."""
    best = max(c.envido_value for c in cards)
    for a, b in combinations(cards, 2):
        if a.suit == b.suit:
            best = max(best, 20 + a.envido_value + b.envido_value)
    return best


def provable_tantos(cards: Sequence[Card]) -> set[int]:
    """Numbers these cards can show exactly (11.7): any single card, or 20 + a same-suit pair."""
    numbers = {c.envido_value for c in cards}
    numbers |= {
        20 + a.envido_value + b.envido_value for a, b in combinations(cards, 2) if a.suit == b.suit
    }
    return numbers


VALID_DECLARATIONS = tuple(range(0, 8)) + tuple(range(20, 34))


def can_call(calls: Sequence[EnvidoCall], call: EnvidoCall) -> bool:
    return (*calls, call) in VALID_SEQUENCES


def envido_points(
    calls: Sequence[EnvidoCall],
    accepted: bool,
    *,
    pica_pica: bool,
    scores: tuple[int, int],
    winner: int,
) -> int:
    """Points the `winner` team gets for an envido sequence (Anexo B.2/B.3, 11.9).

    No querido = the sum of what was already on the table before the last call (minimum 1).
    """
    if not calls:
        raise ValueError("no envido calls")
    if tuple(calls) not in VALID_SEQUENCES:
        raise ValueError(f"invalid envido sequence: {calls}")
    if not accepted:
        return max(1, sum(_VALUE[c] for c in calls[:-1]))
    if calls[-1] == EnvidoCall.FALTA_ENVIDO:
        if pica_pica:
            return PICA_PICA_FALTA_ENVIDO
        if max(scores) <= MALAS_MAX:
            return TARGET - scores[winner]  # both in malas: it decides the partido
        return TARGET - max(scores)
    return sum(_VALUE[c] for c in calls)
