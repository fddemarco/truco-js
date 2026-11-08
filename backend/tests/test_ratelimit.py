"""Routes anyone can call that write are rate limited per client address, in the database."""

from app import ratelimit
from app.config import get_settings
from app.games import registry
from app.ratelimit import Limit

SEATS = [{"kind": "human"}] + [{"kind": "bot", "bot_preset": "prolijo"}] * 5


def new_game(client, headers: dict | None = None) -> int:
    return client.post(
        "/api/games", json={"mode": "strict", "seats": SEATS}, headers=headers or {}
    ).status_code


def test_creating_games_is_limited_per_window(client, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "games", Limit(2, 600))
    assert [new_game(client) for _ in range(3)] == [201, 201, 429]
    res = client.post("/api/games", json={"mode": "strict", "seats": SEATS})
    assert res.headers["Retry-After"] == "600"
    # Other buckets keep their own count.
    assert client.post("/api/logs", json={"session_id": "s", "entries": []}).status_code == 204


def test_the_window_slides(client, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "games", Limit(1, 0))
    assert [new_game(client) for _ in range(2)] == [201, 201]


def test_forwarded_addresses_count_only_behind_a_trusted_proxy(client, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "games", Limit(1, 600))
    a, b = {"X-Forwarded-For": "1.1.1.1"}, {"X-Forwarded-For": "2.2.2.2, 10.0.0.1"}
    # Untrusted: a forged header doesn't buy a fresh bucket.
    assert [new_game(client, a), new_game(client, b)] == [201, 429]
    monkeypatch.setenv("TRUST_PROXY", "true")
    get_settings.cache_clear()
    assert [new_game(client, a), new_game(client, b), new_game(client, b)] == [201, 201, 429]


def test_logs_and_bots_are_limited(client, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "logs", Limit(1, 60))
    monkeypatch.setitem(ratelimit.LIMITS, "bots", Limit(1, 600))
    batch = {"session_id": "s", "entries": []}
    assert [client.post("/api/logs", json=batch).status_code for _ in range(2)] == [204, 429]
    bot = {"name": "B", "settings": {}}
    assert client.post("/api/bots", json=bot).status_code == 201
    assert client.post("/api/bots", json=bot | {"name": "C"}).status_code == 429


def test_a_full_server_answers_503(client, monkeypatch):
    monkeypatch.setattr(registry, "MAX_LIVE_GAMES", 1)
    assert [new_game(client), new_game(client)] == [201, 503]
