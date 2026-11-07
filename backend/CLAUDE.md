# Backend (FastAPI)

```
app/
  main.py        app factory; routers mounted under /api
  config.py      Settings (env / ../.env): DATA_DIR, CORS_ORIGINS
  db.py          SQLite engine + get_session dependency
  models.py      SQLModel tables + Create/Update/Read schemas
  routers/       one module per resource; each exposes `router`
  truco/         game engine and tournament logic (no FastAPI/DB imports)
    cards.py       Card, Suit, 40-card deck, truco rank (Anexo A)
    envido.py      tanto, valid envido sequences, envido points (11, Anexo B)
    truco.py       truco ladder and points (12)
    rounds.py      ronda winner, pardas table (7)
    table.py       seats, teams, reserved numbers, mano, duelo order (3, 5, 15.4)
    hand.py        Contest (mano redonda or one duelo) + PicaPicaHand: step API
    match.py       Match: deals, redonda/pica-pica alternation, 30 cap, dealing errors, sanctions, results
    standings.py   group standings and tiebreakers (1.13, 1.14)
    signals.py     TODO: señas (Anexo C)
scripts/export_openapi.py   writes ../frontend/openapi.json (used by `make gen-api`)
tests/           pytest; the `client` fixture gives a TestClient on a tmp DATA_DIR
  truco/         engine tests
```

## Truco engine
- Seats 0..5, play moves right = seat + 1. Team 0 sits at even seats, team 1 at odd ones. Same reserved numbers face each other (`facing(seat) = seat + 3`). Mano = right of the dealer.
- Step API (shared by UI and RL): `hand.to_act`, `hand.legal_actions()`, `hand.apply(Action)`, `hand.finished`, `hand.points`. `Match.deal()` starts a mano and `Match.play(action)` applies an action and closes the mano when it ends.
- `Action.kind` values are the Spanish expressions (`quiero`, `no_quiero`, `me_voy_al_mazo`, `real_envido`...).
- Simplified for now (see the docstrings): only the player in turn sings, envido declarations are automatic and truthful, there is no tapar, and claims and referee incidents are not modelled.
- Points the reglamento leaves open, confirmed by the project owner (each has a test):
  - Raising (retruco/vale cuatro) as an answer counts as accepting the previous level.
  - Envido can't be sung once a truco is querido.
  - A mano annulled by a 2nd dealing error still counts toward the redonda/pica-pica alternation.

## Conventions
- Type every route's return value (`-> TeamRead`). FastAPI derives `response_model` and OpenAPI from it, which feeds the frontend types.
- Use sync `def` routes. They run in a threadpool, and SQLite calls block.
- Errors: `raise HTTPException(status, "message")`. The frontend shows `detail`.
- New router: create `app/routers/<name>.py` with `router = APIRouter(prefix="/<name>", tags=["<name>"])`, then add it to the tuple in `app/main.py`.
- New SQLite table: add a `table=True` model in `models.py`. `init_db()` creates tables on startup, and there are no migrations. For schema changes to existing tables during development, run `make clean` or add Alembic when the project needs it.

## Commands (from backend/)
- `uv run pytest -q`, or `uv run pytest tests/truco/test_hand.py -k envido`
- `uv run ruff check --fix . && uv run ruff format .`
- `uv add <pkg>` / `uv add --dev <pkg>`
