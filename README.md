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

## Deploy
Free tiers only: Neon Postgres and Vercel (static SPA + FastAPI as a Python function), with the app's own password gate (`ACCESS_PASSWORD`). Setup, environment variables and checks: [docs/deployment.md](docs/deployment.md).

## Project layout
```
backend/    FastAPI app, truco engine (app/truco), tests
docs/       official reglamento (source of truth for the rules), deployment guide
frontend/   SvelteKit SPA
data/       local state (gitignored)
.claude/    Claude Code skills + auto-format hook (see CLAUDE.md)
```

## Template updates
This project was generated with Copier. To pull in template changes: `uvx copier update`.
