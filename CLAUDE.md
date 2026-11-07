# Truco

Truco tournament webapp with an RL-powered bot

Stack:
- **backend/**: FastAPI (Python 3.12, uv) + the truco engine
- **frontend/**: SvelteKit (SPA, adapter-static) + TypeScript + Tailwind v4

## Architecture

```
UI ──/api (vite proxy)──▶ FastAPI ──▶ SQLite  data/app.sqlite   (SQLModel)
                             │
                             └─ app/truco/   pure-Python game engine + tournament logic
```

- **Two rule modes**, chosen when a tournament or one-off game starts: strict (restricted moves, for the RL bot) and interactive (simulated real table for multiplayer, engine as referee). See `backend/CLAUDE.md`.
- **The rules are the spec.** `docs/reglamento-truco-sepica.md` is the official Se Pica TSA reglamento (Spanish). Engine code cites rule numbers (e.g. `(15.1)`). Check the rule before changing behaviour.
- `backend/app/truco/` has no web or DB dependencies, so the API and the future RL bot share it. See `backend/CLAUDE.md`.
- The UI shows the reglamento in Spanish and English (`frontend/src/lib/rules/`). Game terms (mano, ronda, envido, truco, pica-pica, parda, quiero, irse al mazo, malas/buenas, señas...) stay in Spanish in every language, in UI copy too.
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

1. **Engine changes need tests** in `backend/tests/truco/`, citing the rule they cover. Features not implemented yet are marked `TODO` in the module docstrings. New rules must state which mode(s) they apply to and be tested in each.
2. **After changing any API route or model, run `make gen-api`.** The frontend uses the generated types in `frontend/src/lib/api/schema.d.ts`. Never edit that file by hand.
3. Response models are `*Read` classes in `app/models.py`. Table models are not returned directly when a Read model exists.
4. Add tests with every backend change. For API tests, use the `client` fixture, which runs against a temporary DATA_DIR. Run `make lint test` before calling a task done.
5. A hook auto-formats edited files (ruff for backend, prettier for frontend), so don't hand-format.

## Skills

Use these project skills (in `.claude/skills/`) for common tasks:
- `add-endpoint`: add an API endpoint
- `add-page`: add a UI page
- `run-dev`: start, verify and debug the app locally

See also `backend/CLAUDE.md` and `frontend/CLAUDE.md`.
