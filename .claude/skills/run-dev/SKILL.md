---
name: run-dev
description: Start the app locally, verify it works end-to-end, and debug common local issues (ports, stale types). Use when asked to run, smoke-test or debug the dev environment.
---

# Run & verify locally

## Start
- First time: `make install`.
- Both servers: `make dev`. API at http://localhost:8000 (docs at `/docs`), UI at http://localhost:5173.
- When you start them yourself, run them as background processes: `make dev-api` and `make dev-web` separately, so you can read each one's logs.

## Smoke test
```bash
curl -s localhost:8000/api/health
curl -s localhost:5173/api/health   # through the Vite proxy
```
Then open http://localhost:5173/rules and switch ES/EN in the header.

## Troubleshooting
| Symptom | Fix |
|---|---|
| `Address already in use` | `lsof -i :8000` / `:5173`, or use `make dev API_PORT=8001 WEB_PORT=5174`. |
| Frontend type errors after a backend change | `make gen-api` |
| SQLite errors after a model change (no such column) | `make clean` (deletes local data) |
