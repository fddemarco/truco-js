import pytest
from fastapi.testclient import TestClient

from app import db, warehouse
from app.config import get_settings


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    warehouse.close()

    from app.main import create_app

    with TestClient(create_app()) as c:
        yield c

    warehouse.close()
    get_settings.cache_clear()
    db.get_engine.cache_clear()
