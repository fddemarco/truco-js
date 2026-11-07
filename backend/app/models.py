from datetime import UTC, datetime
from typing import Annotated, Any

from pydantic import ConfigDict, StringConstraints
from sqlmodel import JSON, Column, Field, SQLModel

from app.bots.settings import BotSettings


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
    created_at: datetime = Field(default_factory=utcnow)


class BotConfigCreate(SQLModel):
    name: BotName
    settings: BotSettings


class BotConfigRead(SQLModel):
    model_config = READ_CONFIG

    id: int
    name: str
    settings: BotSettings
    created_at: datetime
