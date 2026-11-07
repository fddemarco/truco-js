"""Scoreboard constants and helpers (1.3–1.5)."""

TARGET = 30
MALAS_MAX = 15  # 0–15 malas, 16–30 buenas


def in_buenas(points: int) -> bool:
    return points > MALAS_MAX


def capped(current: int, gained: int) -> int:
    """New score after gaining points; anything above 30 is discarded (1.5)."""
    return min(TARGET, current + gained)
