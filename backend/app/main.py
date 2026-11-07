import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import warehouse
from app.config import get_settings
from app.db import init_db
from app.routers import data, health, pipelines, runs

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield
    warehouse.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Truco", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    api = APIRouter(prefix="/api")
    for module in (health, pipelines, runs, data):
        api.include_router(module.router)
    app.include_router(api)
    return app


app = create_app()
