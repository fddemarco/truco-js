---
name: add-endpoint
description: Add or change a FastAPI endpoint (route, models, tests) and regenerate the frontend's typed API client. Use for any backend API change.
---

# Add an API endpoint

1. **Models** (`backend/app/models.py`):
   - SQLite-backed resources: `<Name>Base(SQLModel)`, `<Name>(Base, table=True)` with an `id` primary key, `<Name>Create`, `<Name>Update` (all optional fields), and `<Name>Read` with `model_config = READ_CONFIG` and `id: int`.
   - Non-persisted responses: a plain pydantic `BaseModel` next to the router (see `routers/data.py`).
2. **Router**: `backend/app/routers/<name>.py`:
   ```python
   router = APIRouter(prefix="/<name>", tags=["<name>"])

   @router.get("")
   def list_<name>(session: Session = Depends(get_session)) -> list[<Name>Read]: ...
   ```
   - Annotate every return type, because the OpenAPI schema and TS types come from it.
   - Use sync `def`. Use `HTTPException(404, "...")` for missing rows.
   - For DuckDB queries, use `with cursor() as cur:` from `app.warehouse` and parameterized SQL.
3. **Mount**: add the module to the router tuple in `backend/app/main.py`, if it's new.
4. **Test**: `backend/tests/test_<name>.py` using the `client` fixture. Cover the happy path, the 404 and validation cases.
5. **Regenerate types**: `make gen-api`. This updates `frontend/src/lib/api/schema.d.ts`. If you want a short alias, add it in `frontend/src/lib/api/client.ts`, e.g. `export type Foo = Schemas["FooRead"]`.
6. Run `make lint test`. Typecheck errors in the frontend usually mean callers need updating to the new schema.

New table columns aren't migrated. In dev, run `make clean` to recreate `data/app.sqlite`.
