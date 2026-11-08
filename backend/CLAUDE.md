# Backend (FastAPI)

```
app/
  main.py        app factory; routers mounted under /api
  config.py      Settings (env / ../.env): DATA_DIR, CORS_ORIGINS
  db.py          SQLite engine + get_session dependency
  models.py      SQLModel tables + Create/Update/Read schemas (BotConfig: saved bots, with an optional character)
  routers/       one module per resource; each exposes `router` (health, bots, games, logs: frontend log intake)
  observability.py  structlog setup (console + JSON lines in DATA_DIR/logs/app.jsonl) + request-id middleware
  games/
    session.py     GameSession: in-memory Match + seats (human tokens / bots), per-seat views, bots auto-play
    schemas.py     API models for game setup, actions and views
    characters.py  Character (the six avatars) + display names, assign_characters (no repeats), team names
  bots/
    settings.py    BotSettings (card order, envido/truco policies + thresholds, bluff) + 5 PRESETS
    strategy.py    choose_action(hand, settings, rng, seat): local, non-cooperative, strict + interactive
  truco/         game engine and tournament logic (no FastAPI/DB imports)
    config.py      RuleMode (strict | interactive) + GameConfig (mode, señas odds, scoring)
    scoring.py     Scoring: target (malas, pica-pica limit and capping follow it) + points per canto chain (quiero / no quiero; a chain is one family's sequence, defined once; unset = reglamento, no quiero = the querido chain so far); REGLAMENTO
    cards.py       Card, Suit, 40-card deck, truco rank (Anexo A)
    envido.py      tanto, valid envido sequences, envido points (11, Anexo B)
    truco.py       truco ladder and points (12)
    rounds.py      ronda winner, pardas table (7)
    table.py       seats, teams, reserved numbers, mano, duelo order, 3-3 physical layout (3, 5, 15.4)
    hand.py        Contest (mano redonda or one duelo) + PicaPicaHand: step API, both modes
    match.py       Match: deals, redonda/pica-pica alternation, 30 cap, reclamos, señas, sanctions, results
    standings.py   group standings and tiebreakers (1.13, 1.14)
    edition.py     Edition (rule mode + phases): group draw, round robin, qualifiers, bracket, warning accumulation (1.8, 19.2)
    signals.py     Sena catalogue (Anexo C), body spots, SenaSeen (strict), SenaEvent (interactive)
scripts/export_openapi.py   writes ../frontend/openapi.json (used by `make gen-api`)
tests/           pytest; the `client` fixture gives a TestClient on a tmp DATA_DIR
  truco/         engine tests
  bots/          bot strategy tests
```

## Truco engine
- Seats 0..5, play moves right = seat + 1. Team 0 sits at even seats, team 1 at odd ones. Same reserved numbers face each other (`facing(seat) = seat + 3`). Mano = right of the dealer.
- Step API (shared by UI and RL): `actions_for(seat)`, `apply(action, seat)`, `to_act`, `finished`, `points`. `Contest.phase` (`PLAYING`, `ANSWERING`, `DECLARING`, `FINISHED`) decides who acts and the legal moves; transitions go through `_enter` (see `docs/state-machine.md`). `Match.phase` is `MatchPhase`. `legal_actions()` and `apply(action)` default to `to_act`. `Match.deal()` starts a mano (and is the cut that closes reclamos), `Match.play(action, seat)` applies one, `Match.sena(event)` records an interactive seña.
- `Action.kind` values are the Spanish expressions (`quiero`, `no_quiero`, `me_voy_al_mazo`, `real_envido`, `son_buenas`...).
- Two rule modes (`GameConfig.mode`), chosen when a tournament or one-off game starts:
  - **Strict** (RL, tight rules): only `to_act` acts, only the player in turn sings, envido is resolved automatically and truthfully, and a seña (`ActionKind.SENA`) is a free action once per turn that each teammate notices with probability `sena_notice_p` and each rival detects with `sena_leak_q` (`Contest.senas_seen(seat)`).
  - **Interactive** (multiplayer, real table, engine as referee): any active player may sing out of turn, and cantos fuera de turno lapse when a card is played. Irregular cantos can be objected (`objetar`), and the last canto can be pardoned by agreement. Envido is declared by the players with bluffing (`declarar`/`son_buenas`) and checked on `reclamar`. Also: `tapar`, `mostrar`, future-duelo concessions, and timed `SenaEvent`s; a seña from outside the duelo is interference.
- The deal is automated, so physical incidents (dealing errors, cutting, dropped/lost cards) are not modelled.
- `Contest.truco_calls` is the truco chain sung (a jump left unobjected is its own chain), for its points.
- Points the reglamento leaves open, confirmed by the project owner (each has a test):
  - Raising (retruco/vale cuatro) as an answer counts as accepting the previous level.
  - Envido can't be sung once a truco is querido.

## Games and multiplayer
- `/api/games`: create (mode + 6 seats, human or bot, optional character per seat, team names and `scoring`: target + chains; tournaments always use the reglamento), `GET /api/games/scoring` (the chains with the reglamento's points), join a seat (returns a token), get the view (`?token=` for a seat's private cards and actions), act, deal the next mano, interactive señas.
- Sessions are in memory: restarting the API drops running games. Clients poll the view (`version` changes on every move). Every move (action or deal) closes a `Step`: its events plus the view of each human seat and a spectator right after it. A view carries the steps after the request's `since`; without `since` (arriving), the current mano's steps since the viewer's last move, from `base`. Clients show those views as they animate; they never rebuild state from events. A device holding every human token is local multiplayer; one token per device is online multiplayer.
- Characters: chosen ones are kept (a repeat loses it), a saved bot brings its own, the rest take a free one. A preset bot is named after its character, a saved bot keeps its name. Team names are drawn from a list unless given. The view has `team_names`, `mano` and `pie`.
- Bots play right after each human move, while `to_act` is a bot. A game starts once every human seat has joined; the first mano is dealt by the table (`deal`, after the shuffle and cut) like every other one.
- Seating is a 3-3 table (`table.side`, `across`, `seats_across`): seats 0-1-2 on one side, 3-4-5 continuing around. A seat's view (`look` on GET and on every POST) only carries the señas of the player across its camera is on, plus its own; spectators see all. `SeatView.played` keeps each seat's cards of the mano (all duelos) until the next deal.

## Logging
- Structured only: `log = structlog.get_logger("area")`, then `log.info("area.what", key=value, ...)`. Event names are dotted and stable; values are fields, never formatted into the message.
- Every request has a `request_id` (from `X-Request-ID` or new), bound to all its lines and echoed in the response. Game lines carry `game_id` (and `seat`). `http.request` is the access log (status, duration_ms); polling GETs log at debug.
- Settings: `LOG_LEVEL` (INFO), `LOG_FORMAT` (console | json), `LOG_FILE` (true). Frontend entries arrive via `POST /api/logs` with `source="frontend"` and `session_id`.
- Errors: `log.exception(...)` keeps the stack. Tests read logs with `structlog.testing.capture_logs()`.

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
