# Truco

Truco tournament webapp with an RL-powered bot

**Stack:** FastAPI · SQLModel (SQLite locally, Postgres on Vercel) · pure-Python truco engine · SvelteKit + TypeScript + Tailwind

The game follows the official [Se Pica TSA reglamento](docs/reglamento-truco-sepica.md).

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically)
- Node 20+ and [pnpm](https://pnpm.io/) 10+
- make

## Quick start
```bash
make install
make dev            # API http://localhost:8000/docs · UI http://localhost:5173
```
Open the UI to read the reglamento in Spanish or English.

## Common tasks
```bash
make help           # all targets
make test           # pytest + vitest
make lint           # ruff + typecheck + prettier
make gen-api        # regenerate frontend API types after backend changes
make clean          # wipe local data (SQLite)
make gen-reqs       # regenerate requirements.txt (Vercel) after changing backend deps
```

## Deploy to Vercel
1. Import the repo in Vercel, root directory = repo root. `vercel.json` sets the build (SPA from `frontend/`), the Python function (`api/index.py`) and the rewrites.
2. Add a Postgres database: Storage → Neon, connected to the project. It sets `DATABASE_URL` (use the pooled URL).
3. Set `STATE_KEY` (at least 32 characters, e.g. `openssl rand -base64 32`; it signs the stored game state, and the API won't start without it), `LOG_FILE=false` and `LOG_FORMAT=json` in the project's environment variables.
4. Deploy. `/api/health` should return `{"status": "ok"}`, and tables are created on the first request.

## Project layout
```
backend/    FastAPI app, truco engine (app/truco), tests
docs/       official reglamento (source of truth for the rules)
frontend/   SvelteKit SPA
data/       local state (gitignored)
.claude/    Claude Code skills + auto-format hook (see CLAUDE.md)
```

## Template updates
This project was generated with Copier. To pull in template changes: `uvx copier update`.
