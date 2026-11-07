---
name: run-dev
description: Start the app locally, verify it works end-to-end, and debug common local issues (ports, DuckDB locks, stale types). Use when asked to run, smoke-test or debug the dev environment.
---

# Run & verify locally

## Start
- First time: `make install`.
- Both servers: `make dev`. API at http://localhost:8000 (docs at `/docs`), UI at http://localhost:5173.
- When you start them yourself, run them as background processes: `make dev-api` and `make dev-web` separately, so you can read each one's logs.

## Smoke test (API)
```bash
curl -s localhost:8000/api/health
curl -s -X POST localhost:8000/api/pipelines -H 'content-type: application/json' \
  -d '{"name":"smoke","source":"example","params":{"rows":10}}'
curl -s -X POST localhost:8000/api/pipelines/1/run
curl -s localhost:8000/api/runs | python3 -m json.tool
curl -s localhost:8000/api/data/tables
curl -s localhost:5173/api/health   # through the Vite proxy
```

## Troubleshooting
| Symptom | Fix |
|---|---|
| `IO Error: Could not set lock on file ... warehouse.duckdb` | Another process holds DuckDB, e.g. a second API, a `duckdb` CLI, or `make dbt-build` while the API runs. Stop it. Find it with `lsof data/warehouse.duckdb`. |
| `Address already in use` | `lsof -i :8000` / `:5173`, or use `make dev API_PORT=8001 WEB_PORT=5174`. |
| Frontend type errors after a backend change | `make gen-api` |
| SQLite errors after a model change (no such column) | `make clean` (deletes local data) |
| Run stuck in `running` after a crash or restart | It was interrupted. Trigger the run again. |
| Want to inspect data by hand | Stop the API first, then `cd backend && uv run python -c "import duckdb; print(duckdb.connect('../data/warehouse.duckdb').sql('show all tables'))"` |
