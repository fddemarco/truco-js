"""The access gate (app/access.py): with ACCESS_PASSWORD set, only health and the gate answer
without the password's cookie."""

import time

import pytest

from app import access, ratelimit
from app.config import get_settings
from app.ratelimit import Limit

SEATS = [{"kind": "human"}] + [{"kind": "bot", "bot_preset": "prolijo"}] * 5


def new_game(client):
    return client.post("/api/games", json={"mode": "strict", "seats": SEATS})


def set_password(monkeypatch, password: str) -> None:
    monkeypatch.setenv("ACCESS_PASSWORD", password)
    get_settings.cache_clear()


def tampered(token: str) -> str:
    return token[:-1] + ("1" if token[-1] == "0" else "0")


@pytest.fixture
def gated(client, monkeypatch):
    set_password(monkeypatch, "pica-pica")
    return client


def test_without_a_password_everything_is_open(client):
    assert client.get("/api/access").json() == {"required": False, "granted": True}
    assert new_game(client).status_code == 201


def test_the_gate_refuses_the_api_without_the_cookie(gated):
    assert gated.get("/api/access").json() == {"required": True, "granted": False}
    res = new_game(gated)
    assert res.status_code == 401
    assert res.json()["detail"] == "access_required"
    assert gated.get("/api/bots").status_code == 401
    assert gated.post("/api/logs", json={"session_id": "s", "entries": []}).status_code == 401
    assert gated.get("/api/health").status_code == 200


def test_a_wrong_password_sets_no_cookie(gated):
    res = gated.post("/api/access", json={"password": "truco"})
    assert res.status_code == 401
    assert access.COOKIE not in res.cookies
    assert new_game(gated).status_code == 401


def test_the_password_opens_the_api(gated):
    res = gated.post("/api/access", json={"password": "pica-pica"})
    assert res.status_code == 200
    assert res.json() == {"required": True, "granted": True}
    assert "httponly" in res.headers["set-cookie"].lower()
    assert gated.get("/api/access").json()["granted"] is True
    assert new_game(gated).status_code == 201


def test_leaving_drops_the_cookie(gated):
    gated.post("/api/access", json={"password": "pica-pica"})
    assert gated.delete("/api/access").status_code == 204
    assert new_game(gated).status_code == 401


def test_a_new_password_logs_everyone_out(gated, monkeypatch):
    gated.post("/api/access", json={"password": "pica-pica"})
    set_password(monkeypatch, "vale-cuatro")
    assert new_game(gated).status_code == 401


@pytest.mark.parametrize(
    "token",
    [
        lambda: access.issue_token(now=time.time() - access.MAX_AGE_S - 1),  # expired
        lambda: tampered(access.issue_token()),
        lambda: f"{int(time.time()) + 1}.{access.issue_token().split('.')[1]}",  # other time
        lambda: "not-a-token",
        lambda: access.issue_token(now=time.time() + 3600),  # issued in the future
    ],
)
def test_bad_cookies_are_refused(gated, token):
    gated.cookies.set(access.COOKIE, token())
    assert new_game(gated).status_code == 401


def test_password_attempts_are_rate_limited(gated, monkeypatch):
    monkeypatch.setitem(ratelimit.LIMITS, "access", Limit(2, 600))
    codes = [gated.post("/api/access", json={"password": "x"}).status_code for _ in range(3)]
    assert codes == [401, 401, 429]
    # The limit holds for the right password too.
    assert gated.post("/api/access", json={"password": "pica-pica"}).status_code == 429
