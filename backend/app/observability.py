"""Structured logging and request tracing.

Every log line is a structured event (an `event` name plus key-value fields), never a
formatted sentence, so it can be filtered and joined:

- Console: readable key=value lines in development, JSON when `LOG_FORMAT=json`.
- File: always JSON lines in `DATA_DIR/logs/app.jsonl` (rotated), for tooling and debugging.
- Context: `request_id` (from the `X-Request-ID` header, or a new one), and `game_id` / `seat`
  where a game is involved, are bound per request with contextvars and added to every line
  logged while handling it, including uvicorn's and the stdlib's.
- Frontend logs arrive through `POST /api/logs` and are written with `source="frontend"` and the
  browser's `session_id`, so a click in the UI and the requests it caused share ids.

Event names are dotted, `area.what` (`http.request`, `game.action`), and stable: they are an
interface for whoever reads the logs.
"""

from __future__ import annotations

import logging
import logging.handlers
import sys
import time
import uuid
from typing import Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import Settings

REQUEST_ID_HEADER = "x-request-id"

log = structlog.get_logger("app")


def _shared_processors() -> list[Any]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]


def configure_logging(settings: Settings) -> None:
    """Route structlog and the stdlib (uvicorn, sqlalchemy...) through the same pipeline."""
    shared = _shared_processors()
    structlog.configure(
        processors=[
            *shared,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        # Not cached: loggers pick up reconfiguration (tests capture logs this way).
        cache_logger_on_first_use=False,
    )

    def formatter(renderer: Any) -> structlog.stdlib.ProcessorFormatter:
        return structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                structlog.processors.format_exc_info,
                renderer,
            ],
        )

    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(
        formatter(
            structlog.processors.JSONRenderer()
            if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer(colors=sys.stderr.isatty())
        )
    )
    handlers: list[logging.Handler] = [console]
    if settings.log_file:
        path = settings.data_dir / "logs" / "app.jsonl"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file = logging.handlers.RotatingFileHandler(
                path, maxBytes=5_000_000, backupCount=3, encoding="utf-8"
            )
        except OSError as e:  # a read-only filesystem (serverless): the console is enough
            print(f"log file disabled: {e}", file=sys.stderr)
        else:
            file.setFormatter(formatter(structlog.processors.JSONRenderer()))
            handlers.append(file)

    root = logging.getLogger()
    root.handlers = handlers
    root.setLevel(settings.log_level.upper())
    # uvicorn's own access log duplicates http.request below.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True


class RequestContextMiddleware:
    """Bind a request id to everything logged during a request, echo it in the response, and
    log one `http.request` line per request with its status and duration."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers") or [])
        incoming = headers.get(REQUEST_ID_HEADER.encode(), b"").decode("latin-1")[:64]
        request_id = incoming or uuid.uuid4().hex[:16]
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message.setdefault("headers", [])
                message["headers"].append((REQUEST_ID_HEADER.encode(), request_id.encode()))
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        except Exception:
            log.exception("http.unhandled_error", method=scope["method"], path=scope["path"])
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            fields = {
                "method": scope["method"],
                "path": scope["path"],
                "status": status,
                "duration_ms": duration_ms,
            }
            # Polling is constant noise: successful GETs of a game go to debug.
            quiet = scope["method"] == "GET" and status < 400 and "/games/" in scope["path"]
            if status >= 500:
                log.error("http.request", **fields)
            elif status >= 400:
                log.warning("http.request", **fields)
            elif quiet or scope["path"] == "/api/logs":
                log.debug("http.request", **fields)
            else:
                log.info("http.request", **fields)
            structlog.contextvars.clear_contextvars()
