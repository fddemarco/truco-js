"""Registry of available dlt sources.

A ``Pipeline`` row in SQLite references a source by its key here; its
``params`` dict is passed to the factory as keyword arguments.
"""

from collections.abc import Callable
from typing import Any

from app.etl.sources.example import example_source

SOURCES: dict[str, Callable[..., Any]] = {
    "example": example_source,
}


def get_source(key: str, params: dict[str, Any]) -> Any:
    try:
        factory = SOURCES[key]
    except KeyError:
        raise ValueError(f"Unknown source {key!r}. Available: {sorted(SOURCES)}") from None
    return factory(**params)
