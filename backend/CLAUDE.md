# Backend (FastAPI)

```
app/
  main.py        app factory; routers mounted under /api (the `backend` service on Vercel, see ../vercel.json)
  config.py      Settings (env / ../.env): DATA_DIR, DATABASE_URL, STATE_KEY, ACCESS_PASSWORD, TRUST_PROXY, CORS_ORIGINS, logging
  access.py      the access gate: one shared password (ACCESS_PASSWORD) → a signed 30-day cookie; `require_access` guards every router but health and access
  db.py          engine (SQLite in DATA_DIR, or Postgres from DATABASE_URL; tables created on first use) + get_session dependency
  models.py      SQLModel tables + Create/Update/Read schemas (BotConfig: saved bots, with an optional character and the hash of their creator's token; GameRecord: a signed pickle of a running game with its optimistic `revision`; GameStep: one signed pickled step per row; RateHit: one rate-limited request; all three internal; WinRate: one row of the hand-strength table written by `experiments/win_rates.py`, read as WinRateRead / WinRatePage)
  routers/       one module per resource; each exposes `router` (health, access: the password gate, bots, games, logs: frontend log intake, analytics: read-only analytical tables)
  observability.py  structlog setup (console + JSON lines in DATA_DIR/logs/app.jsonl) + request-id middleware
  signing.py     seal/unseal: pickles signed with STATE_KEY (HMAC-SHA256), checked before unpickling; the local key file
  ratelimit.py   per-address rate limits kept in the database (`rate_limited(bucket)` route dependency, LIMITS)
  games/
    session.py     GameSession: Match + seats (human tokens / bots), moves, steps, bots auto-play, the table's deal (deal_at / tick), host token + seat reset, presence
    views.py       per-seat GameView, steps since `since`, card/action model conversions
    registry.py    running games, stored only in the database: run() loads, deals if due, acts, saves (optimistic, retried); sweep of idle games; MAX_LIVE_GAMES cap
    schemas.py     API models for game setup, actions and views
    characters.py  Character (the six avatars) + display names, assign_characters (no repeats), team names
    stats.py       PartidoLog (cards dealt + moves) and facts(): the end screen's fun facts
  bots/
    settings.py    BotSettings (card order, envido/truco policies + thresholds, bluff) + 5 PRESETS
    strategy.py    choose_action(hand, settings, rng, seat): local, non-cooperative, strict + interactive
  truco/         game engine (no FastAPI/DB imports)
    config.py      RuleMode (strict | interactive), Format (reglamento | redonda | pica_pica) + GameConfig (mode, format → players/partners, señas odds, scoring)
    scoring.py     Scoring: target (malas, pica-pica limit and capping follow it) + points per canto chain (quiero / no quiero; a chain is one family's sequence, defined once; unset = reglamento, no quiero = the querido chain so far); REGLAMENTO
    cards.py       Card, Suit, 40-card deck, truco rank (Anexo A)
    envido.py      tanto, valid envido sequences, envido points (11, Anexo B)
    truco.py       truco ladder (12)
    rounds.py      ronda winner, pardas table (7)
    table.py       seats, teams, reserved numbers, mano, duelo order, 3-3 physical layout (3, 5, 15.4)
    hand.py        Contest (mano redonda or one duelo) + PicaPicaHand: step API, both modes
    match.py       Match: deals, redonda/pica-pica alternation, 30 cap, reclamos, señas, warnings (19.2), result
    signals.py     Sena catalogue (Anexo C), body spots, SenaSeen (strict), SenaEvent (interactive)
scripts/export_openapi.py   writes ../frontend/openapi.json (used by `make gen-api`)
tests/           pytest; the `client` fixture gives a TestClient on a tmp DATA_DIR
  truco/         engine tests
  bots/          bot strategy tests
```

## Truco engine
- Seats 0..5, play moves right = seat + 1. Team 0 sits at even seats, team 1 at odd ones. Same reserved numbers face each other (`facing(seat) = seat + 3`). Mano = right of the dealer.
- Step API (shared by UI and RL): `actions_for(seat)`, `apply(action, seat)`, `to_act`, `finished`, `points`. `Contest.phase` (`PLAYING`, `ANSWERING`, `DECLARING`, `FINISHED`) decides who acts and the legal moves; transitions go through `_enter` (see `docs/state-machine.md`). `legal_actions()` and `apply(action)` default to `to_act`. `Match.deal()` starts a mano (and is the cut that closes reclamos), `Match.play(action, seat)` applies one, `Match.sena(event)` records an interactive seña.
- `Action.kind` values are the Spanish expressions (`quiero`, `no_quiero`, `me_voy_al_mazo`, `real_envido`, `son_buenas`...).
- Two rule modes (`GameConfig.mode`), chosen when a tournament or one-off game starts:
  - **Strict** (RL, tight rules): only `to_act` acts, only the player in turn sings, envido is resolved automatically and truthfully, and a seña (`ActionKind.SENA`) is a free action once per turn that each teammate across the table notices with probability `sena_notice_p` and each rival across it detects with `sena_leak_q` (in redonda, faces on your own side can't be seen, 14.4) (`Contest.senas_seen(seat)`).
  - **Interactive** (multiplayer, real table, engine as referee): any active player may sing out of turn, and cantos fuera de turno lapse when a card is played. Irregular cantos can be objected (`objetar`), and the last canto can be pardoned by agreement. Envido is declared by the players with bluffing (`declarar`/`son_buenas`) and checked on `reclamar`. Also: `tapar`, `mostrar`, future-duelo concessions, and timed `SenaEvent`s; a seña from outside the duelo is interference.
- Formats (`GameConfig.format`), each in both modes: `reglamento` (6 seats, redondas alternating with pica-pica, 15.1), `redonda` (6 seats, every mano redonda) and `pica_pica` (2 seats, one against one: every mano is one `Contest` of seats 0 and 1 with `hand_kind` pica_pica, scored like a mano, so falta envido is what the leader lacks, not 6; no partners, so no señas, strict or timed, and no `nos_vamos_al_mazo`). Table helpers that go around the table (`right_of`, `left_of`, `order_from`, `mano_of`, `choose_first_dealer`) take the number of `players`.
- The deal is automated, so physical incidents (dealing errors, cutting, dropped/lost cards) are not modelled.
- `Contest.truco_calls` is the truco chain sung (a jump left unobjected is its own chain), for its points.
- Points the reglamento leaves open, confirmed by the project owner (each has a test):
  - Raising (retruco/vale cuatro) as an answer counts as accepting the previous level.
  - Envido can't be sung once a truco is querido.

## Games and multiplayer
- `/api/games`: create (mode, `format` + its seats: 6, or 2 for pica_pica, else 422; joining a seat the table doesn't have is 409; human or bot, optional character per seat, team names and `scoring`: target + chains; tournaments always use the reglamento; returns the id and the `host_token`), `GET /api/games/scoring` (the chains with the reglamento's points), join a seat (name, optional character kept if free; returns a token), get the view, act, cut (`/deal`), interactive señas, `/seats/{seat}/reset` (host only).
- Tokens travel in headers, never in URLs: `X-Seat-Token` (a seat's private cards and actions; required on moves, optional on GET: none is a spectator) and `X-Host-Token` (seat reset). Saved bots: anyone lists and plays them, but changing or deleting one takes the `X-Bot-Token` returned once when it was created (bots saved before tokens can't be changed). Errors: unknown token 403, missing header 422.
- Access: with `ACCESS_PASSWORD` set, every route but `/api/health` and `/api/access` answers 401 `access_required` without the `truco_access` cookie, which `POST /api/access` sets for the right password (wrong: 401 `wrong_password`). The cookie is `<issued_at>.<hmac>` under `STATE_KEY` over the time and a fingerprint of the password, so a new password or key logs everyone out. Tests turn it on with `ACCESS_PASSWORD` + `get_settings.cache_clear()` (`tests/test_access.py`); the `client` fixture has it off.
- Abuse limits: creating games or bots, password attempts and `POST /api/logs` are rate limited per client address (`app/ratelimit.py`, 429 with `Retry-After`); the address is X-Forwarded-For's first hop only with `TRUST_PROXY` (default on Vercel). No game is created past `MAX_LIVE_GAMES` unfinished ones (503).
- **Stateless, for serverless (Vercel):** nothing about a game lives in process memory between requests and nothing runs between them. Every game route goes through `registry.run(game_id, fn, since)`: it loads the `GameRecord` (a pickled `GameSession`) and the `GameStep` rows the view can need (after `since`, or from the step before the current mano's deal, `deal_step`), deals if `deal_at` has passed, calls `fn`, and saves if the game changed. Saves are optimistic: `UPDATE ... WHERE revision = <loaded>`; if another request saved meanwhile, the whole request runs again on the fresh game (up to 3 times, then 409; `game.save_conflict`). A refused move saves nothing, except a deal the tick made. Steps older than the previous mano's deal are deleted. Rows are pickles signed with `STATE_KEY` (`app/signing.py`) and are unpickled only after the signature checks, so write access to the database can't run code here. A row that doesn't verify or no longer unpickles is dropped (`game.restore_failed`, then 404). The API refuses to start with `DATABASE_URL` and no `STATE_KEY`; locally the key is `DATA_DIR/state.key`. Idle games (`IDLE_TTL_S` since their last save, sooner once finished) are swept with their steps when a game is created (`game.swept`).
- The deal is the server's: between manos `deal_at` (epoch ms, in the view with `cutter`) is set, 2 s after the mano for a bot cutter and 10 s for a human one, and the first request after it deals (`GameSession.tick(now)`, called by `registry.run`; clients poll every second, spectators too). The cutter (dealer's left) may cut sooner with `POST /deal`; anyone else gets 403. Tests deal at once with `registry.run(id, lambda g: g.tick(g.deal_at))` or patch `registry.now_ms`.
- Presence: every view or move with a seat token stamps `Seat.last_seen_ms`; `SeatView.online` is a bot or a human seen within 20 s. A stamp alone is saved only once it moved 5 s (`PRESENCE_SAVE_MS`), so polls don't write every time. The host (who created the game) can free a human seat (`reset_seat`): its token stops working and the seat can be joined again from the link, mid-game too. A bot move that raises is logged (`game.bot_failed`) and replaced by its first legal move, so a strategy bug never fails the human's request or stalls the table. Clients poll the view every second (there is no push: serverless functions can't hold a stream). Every move (action or deal) closes a `Step`: its events plus the view of each human seat and a spectator right after it. A view carries the steps after the request's `since`; without `since` (arriving), the current mano's steps since the viewer's last move, from `base`. Clients show those views as they animate; they never rebuild state from events. A device holding every human token is local multiplayer; one token per device is online multiplayer.
- Characters: chosen ones are kept (a repeat loses it), a saved bot brings its own, the rest take a free one. A preset bot is named after its character, a saved bot keeps its name. Team names are drawn from a list unless given. The view has `team_names`, `mano`, `pie` (§2, the last in the order) and `pies` (each team's last), and `stats` once the partido is over. Envido canto events carry `stakes` (quiero per winning team, no quiero); `envido_resuelto` carries the `tantos` the table heard (strict: said in turn from the real tantos by `said_in_order`, so a losing tanto is "son buenas" and never revealed, 11.5; interactive: declared); `reparto` carries the `hand_kind`.
- Bots play right after each human move, while `to_act` is a bot. A game starts once every human seat has joined; the first mano is dealt by the table (at `deal_at`, or when the cutter cuts) like every other one.
- Seating is a 3-3 table (`table.side`, `across`, `seats_across`): seats 0-1-2 on one side, 3-4-5 continuing around. A seat's view (`look` on GET and on every POST) only carries the señas of the player across its camera is on, plus its own; spectators see all. `SeatView.played` keeps each seat's cards of the mano (all duelos) until the next deal.

## Analytics
- `GET /api/analytics/win-rates` (behind the access gate) pages the `win_rate` table, one row per format (`pica_pica` | `redonda`), canto and key: envido rows are a `tanto`, truco rows a set of truco `ranks` (strongest first) and the `policy` (the `CardOrder` every player used). Each has `by_seat` (win rate at each seat counted from the mano: 2 in pica-pica, 6 in redonda, at the deal), `strength` (their mean), `samples` and `exact`. Filters: `format`, `canto`, `policy`, `tanto`, `hand` (three `<number>-<suit>` cards, e.g. `1-espada`: only that hand's tanto and ranks; else 422), `min_strength`/`max_strength`; ordered by `strength` (`descending`, default true), `limit` (≤ 500) and `offset`; returns `total` and `items`.
- Pica-pica rows are exact (envido by inclusion-exclusion over every rival hand, truco by playing every rival hand per pair of rank signatures; `random` branches over every card). Redonda rows are seeded Monte Carlo (`--deals` per signature, `--envido-deals` per tanto), played with the engine's `choose_card`, `round_winner` and `hand_winner`. The API never writes them; `make win-rates` replaces an experiment's rows (format + canto + policy).

## Logging
- Structured only: `log = structlog.get_logger("area")`, then `log.info("area.what", key=value, ...)`. Event names are dotted and stable; values are fields, never formatted into the message.
- Every request has a `request_id` (from `X-Request-ID` or new), bound to all its lines and echoed in the response. Game lines carry `game_id` (and `seat`). `http.request` is the access log (status, duration_ms); polling GETs log at debug.
- Settings: `LOG_LEVEL` (INFO), `LOG_FORMAT` (console | json), `LOG_FILE` (true; on a read-only filesystem it falls back to the console alone), `LOG_MAX_MB` (5) and `LOG_BACKUPS` (3) for the file's rotation. `make dev` rolls the file over before starting (`python -m app.observability rotate`), so each run starts empty and the previous one is `app.jsonl.1`; `--reload` restarts don't. Frontend entries arrive via `POST /api/logs` with `source="frontend"` and `session_id`; a client field named like a key the server binds (`request_id`) is kept as `client_<key>`.
- Errors: `log.exception(...)` keeps the stack. Tests read logs with `structlog.testing.capture_logs()`.

## Conventions
- Type every route's return value (`-> TeamRead`). FastAPI derives `response_model` and OpenAPI from it, which feeds the frontend types.
- Use sync `def` routes. They run in a threadpool, and database calls block.
- Errors: `raise HTTPException(status, "message")`. The frontend shows `detail`.
- New router: create `app/routers/<name>.py` with `router = APIRouter(prefix="/<name>", tags=["<name>"])`, then add it to the tuple in `app/main.py`.
- New table: add a `table=True` model in `models.py`. `init_db()` creates tables when the engine is first used (not in the lifespan, which serverless runtimes may skip) and adds new columns to existing tables when it can (`add_missing_columns`: nullable ones, or NOT NULL with a constant default such as `revision: int = 0`); there are no other migrations. For other schema changes, run `make clean` locally and drop the table in production, or add Alembic when the project needs it. Keep queries portable: SQLite locally, Postgres on Vercel (`TEST_DATABASE_URL=... uv run pytest` runs the suite on Postgres).

## Commands (from backend/)
- `uv run pytest -q`, or `uv run pytest tests/truco/test_hand.py -k envido`
- `uv run ruff check --fix . && uv run ruff format .`
- `uv add <pkg>` / `uv add --dev <pkg>`
