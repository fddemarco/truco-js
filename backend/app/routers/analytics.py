"""Analytical tables, read-only. Hand strength: written by `experiments/win_rates.py`."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, and_, func, or_, select

from app.bots.settings import CardOrder
from app.db import get_session
from app.models import Canto, WinRate, WinRatePage, WinRateRead
from app.truco.cards import NUMBERS, Card, Suit
from app.truco.config import Format
from app.truco.envido import tanto as tanto_of

router = APIRouter(prefix="/analytics", tags=["analytics"])

CARD = re.compile(r"^(\d{1,2})-([a-z]+)$")


def _card(code: str) -> Card:
    match = CARD.match(code)
    if not match or int(match[1]) not in NUMBERS or match[2] not in set(Suit):
        raise HTTPException(422, f"Invalid card {code!r}: use <number>-<suit>, e.g. 1-espada")
    return Card(int(match[1]), Suit(match[2]))


def _ranks(code: str | None) -> list[int] | None:
    return None if code is None else [int(r) for r in code.split("-")]


@router.get("/win-rates")
def win_rates(
    session: Session = Depends(get_session),
    format: Format | None = None,  # noqa: A002 (the query parameter's name)
    canto: Canto | None = None,
    policy: CardOrder | None = None,
    hand: Annotated[
        list[str], Query(description="three cards: only that hand's tanto and truco ranks")
    ] = [],  # noqa: B006
    tanto: Annotated[int | None, Query(ge=0, le=33)] = None,
    min_strength: Annotated[float | None, Query(ge=0, le=1)] = None,
    max_strength: Annotated[float | None, Query(ge=0, le=1)] = None,
    descending: bool = True,
    limit: Annotated[int, Query(ge=1, le=500)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> WinRatePage:
    """Hand strength for envido (by tanto) and truco (by truco ranks and card order), in
    pica-pica and redonda: the win rate at each seat from the mano and their mean."""
    filters = []
    if format is not None:
        filters.append(WinRate.format == format)
    if canto is not None:
        filters.append(WinRate.canto == canto)
    if policy is not None:
        filters.append(WinRate.policy == policy.value)
    if hand:
        cards = [_card(code) for code in hand]
        if len(set(cards)) != 3:
            raise HTTPException(422, "A hand is three different cards")
        ranks = "-".join(str(c.rank) for c in sorted(cards, key=lambda c: -c.rank))
        filters.append(
            or_(
                and_(WinRate.canto == Canto.ENVIDO, WinRate.tanto == tanto_of(cards)),
                and_(WinRate.canto == Canto.TRUCO, WinRate.ranks == ranks),
            )
        )
    if tanto is not None:
        filters.append(WinRate.tanto == tanto)
    if min_strength is not None:
        filters.append(WinRate.strength >= min_strength)
    if max_strength is not None:
        filters.append(WinRate.strength <= max_strength)

    total = session.exec(select(func.count()).select_from(WinRate).where(*filters)).one()
    by_strength = WinRate.strength.desc() if descending else WinRate.strength.asc()
    rows = session.exec(
        select(WinRate)
        .where(*filters)
        .order_by(by_strength, WinRate.id)
        .offset(offset)
        .limit(limit)
    ).all()
    items = [
        WinRateRead(**r.model_dump(exclude={"id", "ranks"}), ranks=_ranks(r.ranks)) for r in rows
    ]
    return WinRatePage(total=total, items=items)
