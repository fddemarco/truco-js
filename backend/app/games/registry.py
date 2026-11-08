"""Running games, stored in the database and nothing else: every request loads its game, acts
and saves it back (`run`), so any number of short-lived server instances (serverless) can
serve the same table.

- A game is a pickled `GameSession` in `GameRecord`; its steps are pickled one per row in
  `GameStep`, and a request loads only the ones its view can need (after `since`, or from
  the step before the current mano's deal).
- Saves are optimistic: a save lands only on the `revision` it loaded. If another request
  saved meanwhile, the whole request runs again on the fresh game (moves are checked
  against the table as it is then), up to `SAVE_ATTEMPTS` times.
- There is no clock: the table deals when a request (clients poll) finds `deal_at` passed.
- A seat's presence stamp only costs a write once it moved `PRESENCE_SAVE_MS`.
- Idle and finished games are swept when a game is created (`sweep`).

Pickle is fine: the database is written only by this app. On a hosted database that makes
DATABASE_URL a secret worth guarding (whoever can write rows can run code here).
"""

import pickle
import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import and_, or_, update
from sqlmodel import Session, col, delete, select

from app.db import get_engine
from app.games.session import Conflict, GameSession, NotFound, Seat, now_ms
from app.models import GameRecord, GameStep
from app.truco.config import GameConfig

log = structlog.get_logger("game")

IDLE_TTL_S = 6 * 3600  # a game nobody saved for this long is dropped
FINISHED_TTL_S = 3600  # a finished one, sooner
SAVE_ATTEMPTS = 3
PRESENCE_SAVE_MS = 5000  # presence is shown with 20 s of slack (SeatView.online)


@dataclass
class _Loaded:
    game: GameSession
    revision: int
    version: int  # the game's, as loaded
    next_step: int  # steps from here on are new
    seen: list[int]  # each seat's presence stamp, as loaded

    def dirty(self) -> bool:
        game = self.game
        if game.version != self.version or game.next_step != self.next_step:
            return True
        return any(
            s.last_seen_ms - before >= PRESENCE_SAVE_MS
            for s, before in zip(game.seats, self.seen, strict=True)
        )


def create_game(
    config: GameConfig, seats: list[Seat], team_names: tuple[str, str] | None = None
) -> GameSession:
    sweep()
    game = GameSession(secrets.token_urlsafe(6), config, seats, team_names=team_names)
    with Session(get_engine()) as db:
        db.add(GameRecord(id=game.id, state=pickle.dumps(game), finished=False))
        db.commit()
    log.info(
        "game.created",
        game_id=game.id,
        mode=str(config.mode),
        humans=sum(s.kind == "human" for s in seats),
        bots=sum(s.kind == "bot" for s in seats),
    )
    return game


def run[T](game_id: str, fn: Callable[[GameSession], T], since: int | None = None) -> T:
    """Load the game (with the steps after `since`), deal if its wait is over, call `fn` and
    save what changed. Raises `NotFound`, `fn`'s errors, or `Conflict` if the table kept
    changing under this request."""
    for attempt in range(SAVE_ATTEMPTS):
        with Session(get_engine()) as db:
            loaded = _load(db, game_id, since)
            if loaded is None:
                raise NotFound("Game not found")
            game = loaded.game
            game.tick(now_ms())
            try:
                result = fn(game)
            except Exception:
                # A refused move changes nothing, but a deal the tick made is kept.
                if loaded.dirty():
                    _save(db, loaded)
                raise
            if not loaded.dirty() or _save(db, loaded):
                return result
        log.info("game.save_conflict", game_id=game_id, attempt=attempt + 1)
    raise Conflict("the table changed meanwhile, try again")


def load(game_id: str, since: int | None = None) -> GameSession | None:
    """The game as stored (read only: nothing is dealt or saved)."""
    with Session(get_engine()) as db:
        loaded = _load(db, game_id, since)
        return loaded.game if loaded else None


def _load(db: Session, game_id: str, since: int | None) -> _Loaded | None:
    record = db.get(GameRecord, game_id)
    if record is None:
        return None
    try:
        game = pickle.loads(record.state)
        if not isinstance(game, GameSession):
            raise TypeError(type(game).__name__)
    except Exception:
        log.exception("game.restore_failed", game_id=game_id)
        _delete(db, [game_id])
        db.commit()
        return None
    if since is not None:
        first = since + 1
    elif game.deal_step is not None:
        first = max(game.deal_step - 1, 0)  # the table before the deal is the replay's base
    else:
        first = game.next_step
    rows = db.exec(
        select(GameStep.state)
        .where(GameStep.game_id == game_id, GameStep.index >= first)
        .order_by(col(GameStep.index))
    ).all()
    game.steps = [pickle.loads(row) for row in rows]
    return _Loaded(
        game=game,
        revision=record.revision,
        version=game.version,
        next_step=game.next_step,
        seen=[s.last_seen_ms for s in game.seats],
    )


def _save(db: Session, loaded: _Loaded) -> bool:
    """Save the game if nobody did since it was loaded; False if someone did."""
    game = loaded.game
    with game.lock:
        state = pickle.dumps(game)
        steps = [s for s in game.steps if s.index >= loaded.next_step]
        finished = game.match.finished
        keep_from = game.previous_deal_step
    saved = db.exec(
        update(GameRecord)
        .where(col(GameRecord.id) == game.id, col(GameRecord.revision) == loaded.revision)
        .values(
            state=state,
            revision=loaded.revision + 1,
            finished=finished,
            updated_at=datetime.now(UTC),
        )
    )
    if saved.rowcount != 1:
        db.rollback()
        return False
    for step in steps:
        db.add(GameStep(game_id=game.id, index=step.index, state=pickle.dumps(step)))
    if steps and keep_from is not None:
        # Steps older than the last mano are never asked for again.
        db.exec(
            delete(GameStep).where(
                col(GameStep.game_id) == game.id, col(GameStep.index) < keep_from - 1
            )
        )
    db.commit()
    return True


def sweep() -> list[str]:
    """Drop the games nobody saved for a while (finished ones sooner), with their steps."""
    wall = datetime.now(UTC)
    with Session(get_engine()) as db:
        gone = list(
            db.exec(
                select(GameRecord.id).where(
                    or_(
                        col(GameRecord.updated_at) < wall - timedelta(seconds=IDLE_TTL_S),
                        and_(
                            col(GameRecord.finished),
                            col(GameRecord.updated_at) < wall - timedelta(seconds=FINISHED_TTL_S),
                        ),
                    )
                )
            ).all()
        )
        if gone:
            _delete(db, gone)
            db.commit()
            log.info("game.swept", count=len(gone))
    return gone


def _delete(db: Session, game_ids: list[str]) -> None:
    db.exec(delete(GameStep).where(col(GameStep.game_id).in_(game_ids)))
    db.exec(delete(GameRecord).where(col(GameRecord.id).in_(game_ids)))
