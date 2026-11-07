"""Truco ladder and points (cap. 12)."""

from enum import StrEnum


class TrucoCall(StrEnum):
    TRUCO = "truco"
    RETRUCO = "retruco"
    VALE_CUATRO = "vale_cuatro"


LADDER = (TrucoCall.TRUCO, TrucoCall.RETRUCO, TrucoCall.VALE_CUATRO)


def truco_points(accepted_level: int) -> int:
    """Points of the mano given how many truco calls were querido (12.2).

    Sin truco = 1, truco querido = 2, retruco querido = 3, vale cuatro querido = 4.
    A rejected call at level L is worth the previous accepted level, i.e. truco_points(L - 1).
    """
    if not 0 <= accepted_level <= len(LADDER):
        raise ValueError(f"invalid truco level: {accepted_level}")
    return accepted_level + 1


def next_call(level: int) -> TrucoCall | None:
    return LADDER[level] if level < len(LADDER) else None
