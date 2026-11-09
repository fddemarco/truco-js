# Truco

Truco tournament webapp with an RL-powered bot

Stack:
- **backend/**: FastAPI (Python 3.12, uv) + the truco engine
- **frontend/**: SvelteKit (SPA, adapter-static) + TypeScript + Tailwind v4

## Architecture

```
UI ──/api (vite proxy | Vercel rewrite)──▶ FastAPI ──▶ SQLite data/app.sqlite | Postgres on Vercel (SQLModel)
                             │
                             ├─ app/truco/   pure-Python game engine
                             ├─ app/bots/    configurable local bot strategies (strict + interactive)
                             ├─ app/routers/analytics.py  read-only analytical tables (win rates)
                             └─ app/games/   game sessions (stateless: loaded and saved per request): seats, tokens, bots, per-seat views, the deal
```

- **The API is stateless** so it runs as Vercel serverless functions: no game is kept in memory, nothing runs between requests (the table deals when a poll finds its wait over), and clients poll. Don't add background threads, in-process caches of game state, streams or local-disk state. See `backend/CLAUDE.md`.

- **Two rule modes**, chosen when a tournament or one-off game starts: strict (restricted moves, for the RL bot) and interactive (simulated real table for multiplayer, engine as referee). See `backend/CLAUDE.md`.
- **Three formats**, also chosen at the start and played in either mode: reglamento (3 v 3, redondas and pica-pica), redonda (3 v 3, no pica-pica) and pica-pica (1 v 1, two seats, no señas).
- **The rules are the spec.** `docs/reglamento-truco-sepica.md` is the official Se Pica TSA reglamento (Spanish). Engine code cites rule numbers (e.g. `(15.1)`). Check the rule before changing behaviour.
- `backend/app/truco/` has no web or DB dependencies, so the API and the future RL bot share it. See `backend/CLAUDE.md`.
- The UI shows the reglamento in Spanish and English (`frontend/src/lib/rules/`). Game terms (mano, ronda, envido, truco, pica-pica, parda, quiero, irse al mazo, malas/buenas, señas...) stay in Spanish in every language, in UI copy too.
- **Experiments** (`experiments/`) compute analytical tables offline with the engine and write them to the app's database (SQLite, or `DATABASE_URL`); the API only reads them. `experiments/win_rates.py`: hand strength for pica-pica (exact) and redonda (3 v 3, Monte Carlo), compressed to what decides each canto with local bots: envido by tanto, truco by the hand's truco ranks (502 patterns) and the card order every player uses; each row has the win rate at every seat from the mano and their mean (`strength`). About 4k rows in the `win_rate` table behind `GET /api/analytics/win-rates`. Its tests live in `backend/tests/` (`pythonpath` includes the repo root).
- Everything under `data/` is local state and gitignored. `make clean` resets it.
- **Art** (avatars, señas, cards) is made with an image model from `docs/art-prompts.md`. Source images live in `assets/` (gitignored, local). Avatar galleries are cut out and aligned by `tools/art/avatars.py`, a standalone uv script, which also edits señas the model can't draw (mirror, lift brows, patch, Inkscape SVG overlays). Final avatars live flat in `assets/avatars/<character>/` (base, portrait, 8 señas) with no dependencies between them; work files go to `assets/work/`. `pnpm import-art` writes the committed WebPs to `frontend/static/`. The workflow and the review bar for señas are in `docs/art-prompts.md`.

## Commands

| Task | Command |
|---|---|
| Install deps | `make install` |
| Run API (:8000) + UI (:5173) | `make dev` (`HOST=0.0.0.0 make dev` to play online across the network) |
| All tests | `make test` (`make test-api` / `make test-web`) |
| Lint + typecheck | `make lint` |
| Format | `make fmt` |
| Regenerate TS API types | `make gen-api` |
| Process an avatar gallery | `uv run tools/art/avatars.py sheet <character> <gallery>` |
| Edit a seña (mirror, lift, patch, SVG overlay, realign) | `uv run tools/art/avatars.py <command> ...` (`--help` for each) |
| Import approved art | `cd frontend && pnpm import-art [--partial]` |
| Run the backend tests against Postgres | `cd backend && TEST_DATABASE_URL=postgresql://... uv run pytest` (drops its tables) |
| Compute the win-rate tables (~10 min) | `make win-rates` (`ARGS="--format redonda --policy random"`, `--deals`, `--skip-envido`...; `DATABASE_URL=... make win-rates` for Neon) |
| Read the logs (backend + frontend, JSON lines) | `tail -f data/logs/app.jsonl` (`LOG_LEVEL=DEBUG` adds polling; browser debug entries such as beats stay in `window.__trucoLogs`) |

Run Python through uv (`cd backend && uv run ...`) and JS through pnpm (`cd frontend && pnpm ...`). Never use pip or npm.

## Deploy (Vercel)

Step-by-step guide for people: `docs/deployment.md` (keep it in sync with this section). One Vercel project from the repo root with two services (`vercel.json`, Vercel services): `frontend` (root `frontend/`, Vite preset, the static SPA in `build/` with an `index.html` fallback) serves `/*`, and `backend` (root `backend/`, FastAPI preset, `app.main:app`) serves `/api/*` and sees the full path, so routes keep their `/api` prefix. Neither calls the other server-side (the browser calls `/api` on the same domain). The frontend's one binding (`BACKEND_URL`) is only for `vercel dev`, where `/api` requests reach the Vite dev server and its proxy needs the backend's random port. Python dependencies come from `backend/pyproject.toml` + `uv.lock`, the version from `backend/.python-version`. The database is the Neon project linked in `.neon`, declared in `neon.ts` (Postgres only, free tier; `neon deploy` applies it). Env vars in Vercel (Preview and Production): `DATABASE_URL` (the Neon branch's pooled Postgres URL), `STATE_KEY` (required: signs the stored game state, `openssl rand -base64 32`), `ACCESS_PASSWORD` (the app's shared password: Vercel's free plan has no password protection, see `backend/app/access.py`), `LOG_FILE=false`, `LOG_FORMAT=json`. The analytics tables come from `DATABASE_URL=<pooled URL> make win-rates`, run by hand. Never point `TEST_DATABASE_URL` at the `production` branch: the suite drops its tables (use `neon checkout dev --create`). Tables are created on first use; there are no migrations, so a new NOT NULL column without a constant default needs its table dropped (locally: `make clean`).

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
