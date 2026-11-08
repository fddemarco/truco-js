import sqlite3

from fastapi.testclient import TestClient

from app import db
from app.config import get_settings


def test_an_old_database_gets_the_new_nullable_columns(tmp_path, monkeypatch):
    # A database from before BotConfig.character: listing bots failed with
    # "no such column: botconfig.character" until it was deleted.
    with sqlite3.connect(tmp_path / "app.sqlite") as old:
        old.execute(
            "CREATE TABLE botconfig (id INTEGER PRIMARY KEY, name VARCHAR NOT NULL,"
            " settings JSON, created_at DATETIME NOT NULL)"
        )
        old.execute(
            "INSERT INTO botconfig (name, settings, created_at)"
            " VALUES ('Viejo', '{}', '2026-01-01 00:00:00')"
        )
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    from app.main import create_app

    try:
        with TestClient(create_app()) as client:
            res = client.get("/api/bots")
            assert res.status_code == 200, res.text
            assert [(b["name"], b["character"]) for b in res.json()] == [("Viejo", None)]
    finally:
        get_settings.cache_clear()
        db.get_engine.cache_clear()


def test_an_old_database_gets_new_not_null_columns_with_a_default(tmp_path, monkeypatch):
    # A database from before GameRecord.revision (NOT NULL, default 0): creating a game failed
    # with "table gamerecord has no column named revision" until it was deleted.
    with sqlite3.connect(tmp_path / "app.sqlite") as old:
        old.execute(
            "CREATE TABLE gamerecord (id VARCHAR PRIMARY KEY, state BLOB NOT NULL,"
            " finished BOOLEAN NOT NULL, updated_at DATETIME NOT NULL)"
        )
        old.execute("INSERT INTO gamerecord VALUES ('viejo', x'00', 1, '2026-01-01 00:00:00')")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("STATE_KEY", "")
    get_settings.cache_clear()
    db.get_engine.cache_clear()
    from app.main import create_app

    try:
        with TestClient(create_app()) as client:
            bots = [{"kind": "bot", "bot_preset": "prolijo"}] * 5
            res = client.post("/api/games", json={"seats": [{"kind": "human"}, *bots]})
            assert res.status_code == 201, res.text
        with sqlite3.connect(tmp_path / "app.sqlite") as conn:
            columns = {c[1]: c for c in conn.execute("PRAGMA table_info(gamerecord)")}
        _, _, kind, notnull, default, _ = columns["revision"]
        assert (kind, notnull, default) == ("INTEGER", 1, "0")  # old rows took the default
    finally:
        get_settings.cache_clear()
        db.get_engine.cache_clear()


def test_provider_postgres_urls_get_the_psycopg_driver(monkeypatch):
    from app.config import Settings

    for url in ("postgres://u:p@host/db", "postgresql://u:p@host/db"):
        monkeypatch.setenv("DATABASE_URL", url)
        assert Settings().db_url == "postgresql+psycopg://u:p@host/db"


def test_without_a_url_the_database_is_sqlite_in_the_data_dir(tmp_path, monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "fresh"))
    assert Settings().db_url == f"sqlite:///{tmp_path / 'fresh' / 'app.sqlite'}"


def test_the_engine_creates_its_tables_on_first_use(data_dir):
    from sqlalchemy import inspect

    tables = set(inspect(db.get_engine()).get_table_names())
    assert {"botconfig", "gamerecord", "gamestep"} <= tables
