"""Truco ladder and points (cap. 12)."""

from enum import StrEnum


class TrucoCall(StrEnum):
    TRUCO = "truco"
    RETRUCO = "retruco"
    VALE_CUATRO = "vale_cuatro"


LADDER = (TrucoCall.TRUCO, TrucoCall.RETRUCO, TrucoCall.VALE_CUATRO)


def next_call(level: int) -> TrucoCall | None:
    return LADDER[level] if level < len(LADDER) else None
