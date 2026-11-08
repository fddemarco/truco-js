"""Frontend logs: the browser ships its structured log entries here in batches, and they are
written to the same log pipeline with `source="frontend"` (see app/observability.py).

Input comes from browsers, so it is bounded: at most 100 entries per batch, short strings, and
only flat JSON fields. Levels map onto the backend's, so LOG_LEVEL filters both. Each
address may send `LIMITS["logs"]` batches a minute (app/ratelimit.py).
"""

from typing import Any, Literal

import structlog
from fastapi import APIRouter, Response
from pydantic import BaseModel, Field, field_validator

from app.ratelimit import rate_limited

router = APIRouter(prefix="/logs", tags=["logs"])
log = structlog.get_logger("frontend")

MAX_FIELDS = 30
MAX_VALUE = 2000
# Keys the server sets on every record; client fields with these names are dropped.
RESERVED = {"event", "level", "timestamp", "logger", "source", "session_id", "client_ts"}
# Keys the server binds to the request's lines; a client's (the id of one of its API calls) is
# kept as `client_<key>`, so it can't pass for the server's.
CONTEXT = {"request_id"}


class ClientLogEntry(BaseModel):
    ts: str = Field(max_length=40)  # the browser's ISO time of the event
    level: Literal["debug", "info", "warn", "error"]
    event: str = Field(min_length=1, max_length=100)
    fields: dict[str, Any] = {}

    @field_validator("fields")
    @classmethod
    def _flat_and_small(cls, value: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, v in list(value.items())[:MAX_FIELDS]:
            if isinstance(v, (bool, int, float)) or v is None:
                out[key[:60]] = v
            else:
                out[key[:60]] = str(v)[:MAX_VALUE]
        return out


class ClientLogBatch(BaseModel):
    session_id: str = Field(min_length=1, max_length=64)
    entries: list[ClientLogEntry] = Field(max_length=100)


@router.post("", status_code=204, dependencies=[rate_limited("logs")])
def receive_logs(batch: ClientLogBatch) -> Response:
    for e in batch.entries:
        method = {"debug": log.debug, "info": log.info, "warn": log.warning, "error": log.error}
        # Client fields can't overwrite the record's own keys (a clash would raise a TypeError).
        fields = {
            f"client_{k}" if k in CONTEXT else k: v
            for k, v in e.fields.items()
            if k not in RESERVED
        }
        method[e.level](
            e.event, source="frontend", session_id=batch.session_id, client_ts=e.ts, **fields
        )
    return Response(status_code=204)
