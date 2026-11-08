"""Request tracing and frontend log intake (app/observability.py, app/routers/logs.py)."""

from structlog.testing import capture_logs


def test_every_response_carries_a_request_id(client):
    res = client.get("/api/health")
    assert len(res.headers["x-request-id"]) >= 8
    traced = client.get("/api/health", headers={"X-Request-ID": "abc123"})
    assert traced.headers["x-request-id"] == "abc123"  # a caller's id is kept, for tracing


def test_requests_and_game_actions_are_logged_with_their_context(client):
    with capture_logs() as logs:
        res = client.post(
            "/api/games",
            json={"seats": [{"kind": "human"}] + [{"kind": "bot", "bot_preset": "prolijo"}] * 5},
            headers={"X-Request-ID": "req-1"},
        )
    game = res.json()["id"]
    created = next(e for e in logs if e["event"] == "game.created")
    assert created["game_id"] == game and created["bots"] == 5
    access = next(e for e in logs if e["event"] == "http.request")
    assert access["status"] == 201 and access["path"] == "/api/games"
    assert "duration_ms" in access


def test_rejected_moves_are_logged_as_warnings(client):
    game = client.post(
        "/api/games",
        json={"seats": [{"kind": "human"}] + [{"kind": "bot", "bot_preset": "prolijo"}] * 5},
    ).json()["id"]
    token = client.post(f"/api/games/{game}/join", json={"seat": 0}).json()["token"]
    with capture_logs() as logs:
        client.post(
            f"/api/games/{game}/act",
            json={"token": token, "action": {"kind": "vale_cuatro"}},
        )
    rejected = [e for e in logs if e["event"] == "game.action_rejected"]
    assert rejected and rejected[0]["log_level"] == "warning" and rejected[0]["seat"] == 0


def test_frontend_logs_are_written_with_their_session(client):
    batch = {
        "session_id": "s-1",
        "entries": [
            {
                "ts": "2026-11-07T10:00:00Z",
                "level": "info",
                "event": "beat.start",
                "fields": {"kind": "truco", "seat": 3, "event": "overwrite?"},
            },
            {
                "ts": "2026-11-07T10:00:01Z",
                "level": "error",
                "event": "ui.error",
                "fields": {"stack": "x" * 5000},
            },
        ],
    }
    with capture_logs() as logs:
        assert client.post("/api/logs", json=batch).status_code == 204
    beat, error = [e for e in logs if e.get("source") == "frontend"]
    assert beat["event"] == "beat.start" and beat["session_id"] == "s-1" and beat["seat"] == 3
    assert error["log_level"] == "error" and len(error["stack"]) <= 2000


def test_frontend_log_batches_are_bounded(client):
    entry = {"ts": "t", "level": "info", "event": "x"}
    too_many = {"session_id": "s", "entries": [entry] * 101}
    assert client.post("/api/logs", json=too_many).status_code == 422
    bad_level = {"session_id": "s", "entries": [{**entry, "level": "fatal"}]}
    assert client.post("/api/logs", json=bad_level).status_code == 422
