# Truco

Truco tournament webapp with an RL-powered bot

**Stack:** FastAPI · SQLModel/SQLite (config) · dlt → DuckDB (data) · SvelteKit + TypeScript + Tailwind

## Requirements
- [uv](https://docs.astral.sh/uv/) (manages Python 3.12 automatically)
- Node 20+ and [pnpm](https://pnpm.io/) 10+
- make

## Quick start
```bash
make install
make dev            # API http://localhost:8000/docs · UI http://localhost:5173
```
Open the UI, create a pipeline with the `example` source, then click **Run** and look at the result on the **Data** page.

## Common tasks
```bash
make help           # all targets
make test           # pytest + vitest
make lint           # ruff + typecheck + prettier
make gen-api        # regenerate frontend API types after backend changes
make clean          # wipe local data (SQLite, DuckDB, dlt state)
```

## Project layout
```
backend/    FastAPI app, dlt sources (app/etl), tests
frontend/   SvelteKit SPA
data/       local state (gitignored)
.claude/    Claude Code skills + auto-format hook (see CLAUDE.md)
```

## Template updates
This project was generated with Copier. To pull in template changes: `uvx copier update`.
