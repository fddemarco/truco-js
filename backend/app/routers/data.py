"""Read-only browsing of the DuckDB warehouse."""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.warehouse import cursor

router = APIRouter(prefix="/data", tags=["data"])


class Table(BaseModel):
    schema_name: str
    table_name: str
    row_count: int


class Column(BaseModel):
    name: str
    type: str


class TablePreview(BaseModel):
    columns: list[Column]
    rows: list[list[Any]]


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


@router.get("/tables")
def list_tables(include_internal: bool = False) -> list[Table]:
    with cursor() as cur:
        rows = cur.execute(
            """
            SELECT schema_name, table_name, estimated_size
            FROM duckdb_tables()
            WHERE database_name = current_database()
            ORDER BY schema_name, table_name
            """
        ).fetchall()
    return [
        Table(schema_name=s, table_name=t, row_count=n)
        for s, t, n in rows
        if include_internal or not (t.startswith("_dlt") or s.endswith("_staging"))
    ]


@router.get("/tables/{schema_name}/{table_name}")
def preview_table(
    schema_name: str, table_name: str, limit: int = Query(100, ge=1, le=1000)
) -> TablePreview:
    with cursor() as cur:
        exists = cur.execute(
            "SELECT 1 FROM duckdb_tables() WHERE schema_name = ? AND table_name = ?",
            [schema_name, table_name],
        ).fetchone()
        if not exists:
            raise HTTPException(404, "Table not found")
        result = cur.execute(
            f"SELECT * FROM {_quote(schema_name)}.{_quote(table_name)} LIMIT ?", [limit]
        )
        columns = [Column(name=d[0], type=str(d[1])) for d in result.description]
        rows = [list(r) for r in result.fetchall()]
    return TablePreview(columns=columns, rows=rows)
