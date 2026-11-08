"""The access gate: one shared password (ACCESS_PASSWORD) in front of the whole app.

Free hosting tiers have no password screen, so the API keeps people out itself: entering the
password (`POST /api/access`) sets a cookie, and every route but health and the gate itself
answers 401 `access_required` without one. The SPA is static and loads for anyone, but it
can't do anything without the API.

The cookie is `<issued_at>.<mac>`, an HMAC under STATE_KEY (app/signing.py) over the issue
time and a fingerprint of the password, so changing the password or the key logs everyone
out. It lasts `MAX_AGE_S`. Unset ACCESS_PASSWORD (local dev): no gate.
"""

import hashlib
import hmac
import time

from fastapi import HTTPException, Request

from app.config import get_settings
from app.signing import state_key

COOKIE = "truco_access"
MAX_AGE_S = 30 * 24 * 3600


def required() -> bool:
    return bool(get_settings().access_password)


def password_matches(password: str) -> bool:
    expected = get_settings().access_password or ""
    return bool(expected) and hmac.compare_digest(password.encode(), expected.encode())


def _mac(issued_at: int) -> str:
    fingerprint = hashlib.sha256((get_settings().access_password or "").encode()).hexdigest()
    message = f"access:v1:{fingerprint[:16]}:{issued_at}".encode()
    return hmac.new(state_key(), message, "sha256").hexdigest()


def issue_token(now: float | None = None) -> str:
    issued_at = int(time.time() if now is None else now)
    return f"{issued_at}.{_mac(issued_at)}"


def valid(token: str | None, now: float | None = None) -> bool:
    if not token or not required():
        return False
    issued, _, mac = token.partition(".")
    if not issued.isdigit():
        return False
    age = (time.time() if now is None else now) - int(issued)
    return 0 <= age <= MAX_AGE_S and hmac.compare_digest(mac, _mac(int(issued)))


def granted(request: Request) -> bool:
    return not required() or valid(request.cookies.get(COOKIE))


def require_access(request: Request) -> None:
    """A router dependency: 401 `access_required` without the password's cookie."""
    if not granted(request):
        raise HTTPException(401, "access_required")
