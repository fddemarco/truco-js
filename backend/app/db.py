"""The database: SQLite locally (DATA_DIR/app.sqlite), Postgres when DATABASE_URL is set (on
Vercel). Saved bots and running games (see app/models.py).

Tables are created the first time the engine is used, not in the app lifespan: serverless
runtimes don't reliably run it.
"""

from collections.abc import Iterator
from functools import lru_cache

import structlog
from sqlalchemy import Engine, inspect, text
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings

log = structlog.get_logger("app")


@lru_cache
def get_engine() -> Engine:
    settings = get_settings()
    url = settings.db_url
    if url.startswith("sqlite"):
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        engine = create_engine(url, connect_args={"check_same_thread": False})
    else:
        # Serverless: every instance is short-lived, so the provider's pooler pools.
        engine = create_engine(url, poolclass=NullPool, pool_pre_ping=True)
    init_db(engine)
    return engine


def init_db(engine: Engine) -> None:
    from app import models  # noqa: F401  (register tables)

    SQLModel.metadata.create_all(engine)
    add_missing_columns(engine)


def add_missing_columns(engine: Engine) -> None:
    """`create_all` never changes a table that already exists, so a database made before a
    column was added would fail on every query. Add the missing columns that can be added in
    place (nullable ones); anything else needs `make clean`."""
    existing = inspect(engine)
    with engine.begin() as conn:
        for table in SQLModel.metadata.sorted_tables:
            if not existing.has_table(table.name):
                continue
            have = {c["name"] for c in existing.get_columns(table.name)}
            for column in table.columns:
                if column.name in have:
                    continue
                if not column.nullable:
                    log.warning("db.column_missing", table=table.name, column=column.name)
                    continue
                kind = column.type.compile(dialect=engine.dialect)
                conn.execute(text(f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {kind}'))
                log.info("db.column_added", table=table.name, column=column.name)


def get_session() -> Iterator[Session]:
    with Session(get_engine()) as session:
        yield session
