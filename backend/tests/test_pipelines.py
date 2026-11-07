def test_crud(client):
    assert client.get("/api/pipelines/sources").json() == ["example"]

    r = client.post("/api/pipelines", json={"name": "demo", "source": "example"})
    assert r.status_code == 201
    pid = r.json()["id"]

    dup = client.post("/api/pipelines", json={"name": "demo", "source": "example"})
    assert dup.status_code == 409
    bad = client.post("/api/pipelines", json={"name": "x", "source": "nope"})
    assert bad.status_code == 422

    r = client.patch(f"/api/pipelines/{pid}", json={"params": {"rows": 5}})
    assert r.json()["params"] == {"rows": 5}

    assert len(client.get("/api/pipelines").json()) == 1
    assert client.delete(f"/api/pipelines/{pid}").status_code == 204
    assert client.get(f"/api/pipelines/{pid}").status_code == 404


def test_disabled_pipeline_cannot_run(client):
    pid = client.post(
        "/api/pipelines", json={"name": "off", "source": "example", "enabled": False}
    ).json()["id"]
    assert client.post(f"/api/pipelines/{pid}/run").status_code == 409
