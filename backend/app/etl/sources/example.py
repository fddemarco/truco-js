"""Offline example source. Copy this file as a starting point for new sources."""

import random
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import dlt


@dlt.source(name="example")
def example_source(rows: int = 100, seed: int = 42) -> Any:
    @dlt.resource(name="orders", primary_key="id", write_disposition="merge")
    def orders() -> Iterator[dict[str, Any]]:
        rng = random.Random(seed)
        start = datetime(2024, 1, 1, tzinfo=UTC)
        for i in range(1, rows + 1):
            yield {
                "id": i,
                "customer": f"customer_{rng.randint(1, 20)}",
                "amount": round(rng.uniform(5, 500), 2),
                "ordered_at": start + timedelta(hours=i),
            }

    return orders
