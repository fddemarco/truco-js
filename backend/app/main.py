from contextlib import asynccontextmanager

from fastapi import APIRouter, Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.access import require_access
from app.config import get_settings
from app.observability import RequestContextMiddleware, configure_logging, log
from app.routers import access, analytics, bots, games, health, logs
from app.signing import state_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Nothing to start: the database is set up on first use (app/db.py) and the table deals
    # on requests (app/games/registry.py), so serverless runtimes need no lifespan.
    settings = get_settings()
    log.info("app.started", database="url" if settings.database_url else "sqlite")
    yield
    log.info("app.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    state_key()  # a deploy without STATE_KEY fails here, not on its first game
    app = FastAPI(title="Truco", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )
    # Outermost, so the request id covers CORS handling and errors too.
    app.add_middleware(RequestContextMiddleware)

    api = APIRouter(prefix="/api")
    # Behind the password (app/access.py) when ACCESS_PASSWORD is set: all but these two.
    for module in (health, access):
        api.include_router(module.router)
    for module in (analytics, bots, games, logs):
        api.include_router(module.router, dependencies=[Depends(require_access)])
    app.include_router(api)
    return app


app = create_app()
