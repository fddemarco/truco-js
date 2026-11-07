from datetime import UTC, datetime

from pydantic import ConfigDict


def utcnow() -> datetime:
    return datetime.now(UTC)


# Response models: fields with defaults are always present in output, so mark
# them required in the OpenAPI schema (gives non-optional TS types).
READ_CONFIG = ConfigDict(json_schema_serialization_defaults_required=True)
