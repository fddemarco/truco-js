import os

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel

from app import db
from app.config import get_settings

# Run the suite against Postgres too: TEST_DATABASE_URL=postgresql://... uv run pytest
# (its tables are dropped before every test). Unset: a fresh SQLite file per test.
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    """A temporary DATA_DIR (SQLite and logs), or a clean TEST_DATABASE_URL."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    if TEST_DATABASE_URL:
        monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)
        monkeypatch.setenv("STATE_KEY", "test-state-key-" + "x" * 32)
    else:
        monkeypatch.setenv("DATABASE_URL", "")  # also hides one in ../.env
        monkeypatch.setenv("STATE_KEY", "")  # a key file in the tmp DATA_DIR
    monkeypatch.setenv("TRUST_PROXY", "false")
    monkeypatch.setenv("ACCESS_PASSWORD", "")  # the gate is off unless a test turns it on
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    if TEST_DATABASE_URL:
        engine = db.get_engine()
        SQLModel.metadata.drop_all(engine)
        db.init_db(engine)
    yield tmp_path
    get_settings.cache_clear()
    db.get_engine.cache_clear()


@pytest.fixture
def client(data_dir):
    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c
