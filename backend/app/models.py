from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import ConfigDict, StringConstraints
from sqlmodel import JSON, Column, Field, SQLModel

from app.bots.settings import BotSettings
from app.games.characters import Character


def utcnow() -> datetime:
    return datetime.now(UTC)


# Response models: fields with defaults are always present in output, so mark
# them required in the OpenAPI schema (gives non-optional TS types).
READ_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)

BotName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class BotConfig(SQLModel, table=True):
    """A bot saved from the advanced settings, under its own name."""

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    settings: dict[str, Any] = Field(sa_column=Column(JSON))
    character: str | None = None  # its avatar; None = whichever is free at the table
    # SHA-256 of the token its creator got, needed to change or delete it. None: saved before
    # tokens, so nobody can (it can still be played and duplicated).
    owner: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class BotConfigCreate(SQLModel):
    name: BotName
    settings: BotSettings
    character: Character | None = None


class BotConfigUpdate(SQLModel):
    name: BotName | None = None
    settings: BotSettings | None = None
    character: Character | None = None


class BotConfigRead(SQLModel):
    model_config = READ_CONFIG

    id: int
    name: str
    settings: BotSettings
    character: Character | None = None
    created_at: datetime


class BotConfigCreated(BotConfigRead):
    """A new bot, with the token that changes or deletes it (`X-Bot-Token`). Shown only once."""

    token: str


class GameRecord(SQLModel, table=True):
    """A running game, pickled and signed by app/games/registry.py: every request loads it and
    saves it back. Internal: never returned by the API."""

    id: str = Field(primary_key=True)
    state: bytes
    # Bumped by every save; a save only lands on the revision it loaded (optimistic locking).
    revision: int = 0
    finished: bool = False
    updated_at: datetime = Field(default_factory=utcnow, index=True)


class GameStep(SQLModel, table=True):
    """One step of a game (a pickled `session.Step`), stored apart so a request loads only the
    steps its view needs. Internal."""

    game_id: str = Field(primary_key=True)
    index: int = Field(primary_key=True)
    state: bytes


class RateHit(SQLModel, table=True):
    """One request counted by app/ratelimit.py. Internal."""

    id: int | None = Field(default=None, primary_key=True)
    key: str = Field(index=True)  # bucket + keyed hash of the client's address
    at: datetime = Field(default_factory=utcnow, index=True)
