# Backend (FastAPI)

```
app/
  main.py        app factory; routers mounted under /api
  config.py      Settings (env / ../.env): DATA_DIR, CORS_ORIGINS
  db.py          SQLite engine + get_session dependency
  models.py      SQLModel tables + Create/Update/Read schemas
  routers/       one module per resource; each exposes `router`
  truco/         game engine and tournament logic (no FastAPI/DB imports)
    config.py      RuleMode (strict | interactive) + GameConfig
    cards.py       Card, Suit, 40-card deck, truco rank (Anexo A)
    envido.py      tanto, valid envido sequences, envido points (11, Anexo B)
    truco.py       truco ladder and points (12)
    rounds.py      ronda winner, pardas table (7)
    table.py       seats, teams, reserved numbers, mano, duelo order (3, 5, 15.4)
    hand.py        Contest (mano redonda or one duelo) + PicaPicaHand: step API, both modes
    match.py       Match: deals, redonda/pica-pica alternation, 30 cap, reclamos, señas, sanctions, results
    standings.py   group standings and tiebreakers (1.13, 1.14)
    signals.py     Sena catalogue (Anexo C), body spots, SenaSeen (strict), SenaEvent (interactive)
scripts/export_openapi.py   writes ../frontend/openapi.json (used by `make gen-api`)
tests/           pytest; the `client` fixture gives a TestClient on a tmp DATA_DIR
  truco/         engine tests
```

## Truco engine
- Seats 0..5, play moves right = seat + 1. Team 0 sits at even seats, team 1 at odd ones. Same reserved numbers face each other (`facing(seat) = seat + 3`). Mano = right of the dealer.
- Step API (shared by UI and RL): `actions_for(seat)`, `apply(action, seat)`, `to_act`, `finished`, `points`. `legal_actions()` and `apply(action)` default to `to_act`. `Match.deal()` starts a mano (and is the cut that closes reclamos), `Match.play(action, seat)` applies one, `Match.sena(event)` records an interactive seña.
- `Action.kind` values are the Spanish expressions (`quiero`, `no_quiero`, `me_voy_al_mazo`, `real_envido`, `son_buenas`...).
- Two rule modes (`GameConfig.mode`), chosen when a tournament or one-off game starts:
  - **Strict** (RL, tight rules): only `to_act` acts, only the player in turn sings, envido is resolved automatically and truthfully, and a seña (`ActionKind.SENA`) is a free action once per turn that each teammate notices with probability `sena_notice_p` and each rival detects with `sena_leak_q` (`Contest.senas_seen(seat)`).
  - **Interactive** (multiplayer, real table, engine as referee): any active player may sing out of turn, and cantos fuera de turno lapse when a card is played. Irregular cantos can be objected (`objetar`), and the last canto can be pardoned by agreement. Envido is declared by the players with bluffing (`declarar`/`son_buenas`) and checked on `reclamar`. Also: `tapar`, `mostrar`, future-duelo concessions, and timed `SenaEvent`s; a seña from outside the duelo is interference.
- The deal is automated, so physical incidents (dealing errors, cutting, dropped/lost cards) are not modelled.
- Points the reglamento leaves open, confirmed by the project owner (each has a test):
  - Raising (retruco/vale cuatro) as an answer counts as accepting the previous level.
  - Envido can't be sung once a truco is querido.

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
