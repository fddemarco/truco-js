"""DuckDB: the analytical warehouse that dlt loads into.

DuckDB allows a single read-write process per database file. Everything in
this process (API reads, dlt loads, dbt runs) must go through the one shared
connection below. Never call ``duckdb.connect()`` on the warehouse elsewhere.
"""

import threading
from collections.abc import Iterator
from contextlib import contextmanager

import duckdb

from app.config import get_settings

_lock = threading.Lock()
_conn: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    global _conn
    with _lock:
        if _conn is None:
            _conn = duckdb.connect(str(get_settings().duckdb_path))
        return _conn


@contextmanager
def cursor() -> Iterator[duckdb.DuckDBPyConnection]:
    """Thread-local cursor on the shared connection (cursors are not thread-safe)."""
    cur = get_connection().cursor()
    try:
        yield cur
    finally:
        cur.close()


def close() -> None:
    global _conn
    with _lock:
        if _conn is not None:
            _conn.close()
            _conn = None
