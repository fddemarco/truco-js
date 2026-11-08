from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.observability import RequestContextMiddleware, configure_logging, log
from app.routers import bots, games, health, logs


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    log.info("app.started", data_dir=str(get_settings().data_dir))
    yield
    log.info("app.stopped")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
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
    for module in (health, bots, games, logs):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
