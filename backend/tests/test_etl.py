def test_run_example_pipeline_loads_duckdb(client):
    pid = client.post(
        "/api/pipelines", json={"name": "demo", "source": "example", "params": {"rows": 25}}
    ).json()["id"]

    # TestClient runs background tasks before returning the response.
    run = client.post(f"/api/pipelines/{pid}/run").json()
    run = client.get(f"/api/runs/{run['id']}").json()
    assert run["status"] == "success", run["error"]
    assert run["rows_loaded"] == 25

    tables = client.get("/api/data/tables").json()
    assert {"schema_name": "raw", "table_name": "orders", "row_count": 25} in tables

    preview = client.get("/api/data/tables/raw/orders", params={"limit": 3}).json()
    assert len(preview["rows"]) == 3
    assert "amount" in [c["name"] for c in preview["columns"]]


def test_preview_unknown_table(client):
    assert client.get("/api/data/tables/raw/missing").status_code == 404
