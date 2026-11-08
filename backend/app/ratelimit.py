"""Rate limits for the routes anyone can call that write rows (creating games and bots) or
logs (frontend log intake).

Serverless instances share nothing but the database, so the hits live there: one `RateHit`
row per hit, and a client with `hits` in the last `window_s` of a bucket gets 429. Rows older
than the longest window are deleted as hits come in.

The client is its address: the socket's, or X-Forwarded-For's first hop with TRUST_PROXY (on
Vercel). It is stored only as a keyed hash.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from fastapi import Depends, HTTPException, Request
from sqlmodel import Session, col, delete, func, select

from app.config import get_settings
from app.db import get_session
from app.models import RateHit
from app.signing import keyed_hash

log = structlog.get_logger("app")


@dataclass(frozen=True)
class Limit:
    hits: int
    window_s: int


LIMITS = {
    "games": Limit(30, 600),
    "bots": Limit(30, 600),
    # A busy page ships a batch every 2 s; a whole table on one address stays under this.
    "logs": Limit(240, 60),
    # Password attempts (app/access.py).
    "access": Limit(10, 600),
}


def client_address(request: Request) -> str:
    if get_settings().trust_proxy:
        forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if forwarded:
            return forwarded
    return request.client.host if request.client else "unknown"


def check(session: Session, bucket: str, address: str) -> None:
    """Count a hit of `address` on `bucket`, or raise 429 if it is over the limit."""
    limit = LIMITS[bucket]
    now = datetime.now(UTC)
    key = f"{bucket}:{keyed_hash(address)}"
    longest = max(rule.window_s for rule in LIMITS.values())
    session.exec(delete(RateHit).where(col(RateHit.at) < now - timedelta(seconds=longest)))
    recent = session.exec(
        select(func.count())
        .select_from(RateHit)
        .where(col(RateHit.key) == key, col(RateHit.at) >= now - timedelta(seconds=limit.window_s))
    ).one()
    if recent >= limit.hits:
        session.commit()
        log.warning("http.rate_limited", bucket=bucket)
        raise HTTPException(
            429, "Too many requests, try again later", {"Retry-After": str(limit.window_s)}
        )
    session.add(RateHit(key=key, at=now))
    session.commit()


def rate_limited(bucket: str):
    """A route dependency: `@router.post(..., dependencies=[rate_limited("games")])`."""

    def dependency(request: Request, session: Session = Depends(get_session)) -> None:
        check(session, bucket, client_address(request))

    return Depends(dependency)
