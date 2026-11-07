from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import ConfigDict
from sqlmodel import JSON, Column, Field, SQLModel


def utcnow() -> datetime:
    return datetime.now(UTC)


class PipelineBase(SQLModel):
    name: str = Field(index=True, unique=True)
    source: str = Field(description="Key in app.etl.registry.SOURCES")
    dataset: str = Field(default="raw", description="DuckDB schema to load into")
    enabled: bool = True
    params: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Pipeline(PipelineBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow)


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(SQLModel):
    name: str | None = None
    source: str | None = None
    dataset: str | None = None
    enabled: bool | None = None
    params: dict[str, Any] | None = None


# Response models: fields with defaults are always present in output, so mark
# them required in the OpenAPI schema (gives non-optional TS types).
READ_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)


class PipelineRead(PipelineBase):
    model_config = READ_CONFIG

    id: int
    created_at: datetime


class RunStatus(StrEnum):
    pending = "pending"
    running = "running"
    success = "success"
    failed = "failed"


class RunBase(SQLModel):
    pipeline_id: int = Field(foreign_key="pipeline.id", index=True)
    status: RunStatus = RunStatus.pending
    started_at: datetime = Field(default_factory=utcnow)
    finished_at: datetime | None = None
    rows_loaded: int | None = None
    error: str | None = None


class Run(RunBase, table=True):
    id: int | None = Field(default=None, primary_key=True)


class RunRead(RunBase):
    model_config = READ_CONFIG

    id: int
