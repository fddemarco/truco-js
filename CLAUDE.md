# Truco

Truco tournament webapp with an RL-powered bot

Stack:
- **backend/**: FastAPI (Python 3.12, uv)
- **frontend/**: SvelteKit (SPA, adapter-static) + TypeScript + Tailwind v4

## Architecture

```
UI ──/api (vite proxy)──▶ FastAPI ──┬─▶ SQLite  data/app.sqlite       config: pipelines, run history (SQLModel)
                                    └─▶ DuckDB  data/warehouse.duckdb loaded data (dlt)
```

- A **pipeline** is a row in SQLite: `name`, `source` (a key in `backend/app/etl/registry.py`), `dataset` (DuckDB schema) and `params` (kwargs passed to the source factory).
- `POST /api/pipelines/{id}/run` creates a `Run` row and runs dlt as a FastAPI background task (`app/etl/runner.py`). The UI polls `/api/runs`.
- `/api/data/*` browses DuckDB read-only.
- Everything under `data/` is local state and gitignored. `make clean` resets it.

## Commands

| Task | Command |
|---|---|
| Install deps | `make install` |
| Run API (:8000) + UI (:5173) | `make dev` |
| All tests | `make test` (`make test-api` / `make test-web`) |
| Lint + typecheck | `make lint` |
| Format | `make fmt` |
| Regenerate TS API types | `make gen-api` |

Run Python through uv (`cd backend && uv run ...`) and JS through pnpm (`cd frontend && pnpm ...`). Never use pip or npm.

## Rules

1. **DuckDB access goes through `app/warehouse.py` only.** DuckDB allows one read-write process per file. The API, dlt share one connection. Never call `duckdb.connect()` on the warehouse anywhere else. Don't open the file from another process while `make dev-api` is running.
2. **After changing any API route or model, run `make gen-api`.** The frontend uses the generated types in `frontend/src/lib/api/schema.d.ts`. Never edit that file by hand.
3. Response models are `*Read` classes in `app/models.py`. Table models are not returned directly when a Read model exists.
4. Add tests with every backend change (`backend/tests`, using the `client` fixture, which runs against a temporary DATA_DIR). Run `make lint test` before calling a task done.
5. A hook auto-formats edited files (ruff for backend, prettier for frontend), so don't hand-format.

## Skills

Use these project skills (in `.claude/skills/`) for common tasks:
- `add-pipeline`: add a new dlt source
- `add-endpoint`: add an API endpoint
- `add-page`: add a UI page
- `run-dev`: start, verify and debug the app locally

See also `backend/CLAUDE.md` and `frontend/CLAUDE.md`.
