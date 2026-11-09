.DEFAULT_GOAL := help
.PHONY: help install dev dev-api dev-web test test-api test-web lint fmt gen-api build clean win-rates

API_PORT ?= 8000
# 0.0.0.0 lets other machines on the network play (online multiplayer)
HOST ?= 127.0.0.1
WEB_PORT ?= 5173
export API_PORT

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (uv) and frontend (pnpm) dependencies
	cd backend && uv sync
	cd frontend && pnpm install

dev: ## Run API and UI together (Ctrl+C stops both)
	@$(MAKE) -j2 --no-print-directory dev-api dev-web

dev-api: ## Run the FastAPI server with reload (each run starts a fresh log file)
	cd backend && uv run python -m app.observability rotate
	cd backend && uv run uvicorn app.main:app --reload --host $(HOST) --port $(API_PORT)

dev-web: ## Run the Vite dev server (proxies /api to the API)
	cd frontend && pnpm dev --host $(HOST) --port $(WEB_PORT)

test: test-api test-web ## Run all tests

test-api:
	cd backend && uv run pytest

test-web:
	cd frontend && pnpm test

lint: ## Lint + typecheck everything
	cd backend && uv run ruff check . ../tools ../experiments && uv run ruff format --check . ../tools ../experiments
	cd frontend && pnpm lint

fmt: ## Format everything
	cd backend && uv run ruff check --fix . ../tools ../experiments && uv run ruff format . ../tools ../experiments
	cd frontend && pnpm format

gen-api: ## Regenerate the typed frontend API client from FastAPI's OpenAPI schema
	cd backend && uv run python -m scripts.export_openapi
	cd frontend && pnpm gen-api

win-rates: ## Hand strength (pica-pica exact, redonda Monte Carlo) into the database (ARGS="--format redonda --policy random")
	cd backend && uv run python ../experiments/win_rates.py $(ARGS)

build: ## Production build of the frontend
	cd frontend && pnpm build

clean: ## Delete local data (SQLite; needed after a NOT NULL column without a default is added)
	rm -rf data
