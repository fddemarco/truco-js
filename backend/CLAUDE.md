# Backend (FastAPI)

```
app/
  main.py        app factory; routers mounted under /api
  config.py      Settings (env / ../.env): DATA_DIR, CORS_ORIGINS
  db.py          SQLite engine + get_session dependency
  warehouse.py   shared DuckDB connection, used via `with cursor() as cur:`
  models.py      SQLModel tables + Create/Update/Read schemas
  routers/       one module per resource; each exposes `router`
  etl/
    registry.py  SOURCES: source key -> dlt source factory
    sources/     one module per dlt source
    runner.py    executes a pipeline run with dlt and records the result
scripts/export_openapi.py   writes ../frontend/openapi.json (used by `make gen-api`)
tests/           pytest; the `client` fixture gives a TestClient on a tmp DATA_DIR
```

## Conventions
- Type every route's return value (`-> PipelineRead`). FastAPI derives `response_model` and OpenAPI from it, which feeds the frontend types.
- Use sync `def` routes. They run in a threadpool, and DuckDB/SQLite calls block.
- Errors: `raise HTTPException(status, "message")`. The frontend shows `detail`.
- New router: create `app/routers/<name>.py` with `router = APIRouter(prefix="/<name>", tags=["<name>"])`, then add it to the tuple in `app/main.py`.
- New SQLite table: add a `table=True` model in `models.py`. `init_db()` creates tables on startup, and there are no migrations. For schema changes to existing tables during development, run `make clean` or add Alembic when the project needs it.
- DuckDB SQL: always pass values as parameters (`?`). Quote identifiers with `_quote()` from `routers/data.py`.
- In TestClient, background tasks run before the response returns, so tests can assert on a run's final state right away.

## Commands (from backend/)
- `uv run pytest -q`, or `uv run pytest tests/test_etl.py -k name`
- `uv run ruff check --fix . && uv run ruff format .`
- `uv add <pkg>` / `uv add --dev <pkg>`
