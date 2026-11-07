---
name: add-pipeline
description: Add a new dlt data source (API, file, database) that pipelines can load into DuckDB. Use when the user wants to ingest or extract data from a new source.
---

# Add a dlt source

A source is a Python factory registered in `backend/app/etl/registry.py`. A pipeline row in SQLite points at it by key and passes its `params` JSON as keyword arguments.

## Steps

1. **Create** `backend/app/etl/sources/<name>.py`, using `example.py` as the reference:
   ```python
   import dlt
   from dlt.sources.helpers import requests  # retrying requests wrapper

   @dlt.source(name="<name>")
   def <name>_source(base_url: str, api_key: str | None = None, ...):
       @dlt.resource(primary_key="id", write_disposition="merge")
       def items():
           yield from requests.get(f"{base_url}/items").json()
       return items
   ```
   - Every factory argument is configurable from the UI through `params`. Give arguments safe defaults when possible.
   - Choose `write_disposition` deliberately: `append` for event logs, `merge` (needs a `primary_key`) for entities, `replace` for small snapshots.
   - For incremental loads, use `dlt.sources.incremental("updated_at")` as a resource argument.
   - For REST APIs, prefer `dlt.sources.rest_api.rest_api_source({...})` over hand-written pagination.
   - Never hardcode secrets. Read them from params or env (`os.environ`), and document which ones are needed.
2. **Register** the factory in `SOURCES` in `backend/app/etl/registry.py`.
3. **Test**: add `backend/tests/test_<name>_source.py`. Don't make network calls in tests. Either make the source accept injectable data, or monkeypatch the HTTP call, then run the full flow through the API:
   ```python
   pid = client.post("/api/pipelines", json={"name": "t", "source": "<name>", "params": {...}}).json()["id"]
   run = client.post(f"/api/pipelines/{pid}/run").json()
   assert client.get(f"/api/runs/{run['id']}").json()["status"] == "success"
   ```
4. Run `make lint test`. The UI's source dropdown picks up the new key automatically, so no frontend change is needed.
5. If you added a dependency, use `cd backend && uv add <pkg>`. Some sources need a dlt extra, e.g. `uv add "dlt[filesystem]"`.

## Gotchas
- dlt normalizes names to snake_case, and nested lists become child tables (`<table>__<field>`).
- Load into the pipeline's `dataset` (a DuckDB schema). Don't set `dataset_name` inside the source.
- The runner passes the shared DuckDB connection to dlt. Don't create your own destination or connection.
