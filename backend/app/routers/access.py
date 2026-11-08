"""The access gate's routes (app/access.py): whether the password is needed, entering it and
leaving. Password attempts are rate limited per address (`LIMITS["access"]`)."""

import structlog
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app import access
from app.ratelimit import rate_limited

log = structlog.get_logger("access")

router = APIRouter(prefix="/access", tags=["access"])


class AccessRead(BaseModel):
    required: bool
    granted: bool


class AccessRequest(BaseModel):
    password: str = Field(max_length=200)


@router.get("")
def get_access(request: Request) -> AccessRead:
    return AccessRead(required=access.required(), granted=access.granted(request))


@router.post("", dependencies=[rate_limited("access")])
def enter(body: AccessRequest, request: Request, response: Response) -> AccessRead:
    if not access.required():
        return AccessRead(required=False, granted=True)
    if not access.password_matches(body.password):
        log.warning("access.denied")
        raise HTTPException(401, "wrong_password")
    https = request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https"
    response.set_cookie(
        access.COOKIE,
        access.issue_token(),
        max_age=access.MAX_AGE_S,
        httponly=True,
        secure=https,
        samesite="lax",
        path="/",
    )
    log.info("access.granted")
    return AccessRead(required=True, granted=True)


@router.delete("", status_code=204)
def leave(response: Response) -> None:
    response.delete_cookie(access.COOKIE, path="/")
