from sqlmodel import Session

from app.bots.settings import BotSettings
from app.db import get_engine
from app.models import BotConfig


def owner(bot: dict) -> dict:
    return {"X-Bot-Token": bot["token"]}


def test_presets(client):
    presets = client.get("/api/bots/presets").json()
    assert [p["key"] for p in presets] == [
        "prolijo",
        "envidioso",
        "cauteloso",
        "mentiroso",
        "ahorrativo",
    ]
    assert BotSettings.model_validate(presets[0]["settings"]) == BotSettings()


def test_save_list_and_delete_a_bot(client):
    settings = BotSettings(envido_sing="always", truco_sing_threshold=13).model_dump(mode="json")
    res = client.post("/api/bots", json={"name": "  Mi bot  ", "settings": settings})
    assert res.status_code == 201
    bot = res.json()
    assert bot["name"] == "Mi bot"
    assert bot["settings"] == settings

    assert [b["name"] for b in client.get("/api/bots").json()] == ["Mi bot"]
    assert "token" not in client.get("/api/bots").json()[0]
    assert client.delete(f"/api/bots/{bot['id']}", headers=owner(bot)).status_code == 204
    assert client.get("/api/bots").json() == []


def test_names_are_unique_including_presets(client):
    settings = BotSettings().model_dump(mode="json")
    assert (
        client.post("/api/bots", json={"name": "Rápido", "settings": settings}).status_code == 201
    )
    dup = client.post("/api/bots", json={"name": "rápido", "settings": settings})
    assert dup.status_code == 409
    preset = client.post("/api/bots", json={"name": "Prolijo", "settings": settings})
    assert preset.status_code == 409


def test_invalid_settings_or_name_rejected(client):
    bad = BotSettings().model_dump(mode="json") | {"envido_sing_threshold": 40}
    assert client.post("/api/bots", json={"name": "X", "settings": bad}).status_code == 422
    ok = BotSettings().model_dump(mode="json")
    assert client.post("/api/bots", json={"name": "   ", "settings": ok}).status_code == 422


def test_delete_missing_bot(client):
    assert client.delete("/api/bots/99", headers={"X-Bot-Token": "t"}).status_code == 404


def test_update_a_bot(client):
    settings = BotSettings().model_dump(mode="json")
    bot = client.post("/api/bots", json={"name": "Uno", "settings": settings}).json()
    assert bot["character"] is None
    other = client.post("/api/bots", json={"name": "Dos", "settings": settings}).json()
    changed = BotSettings(envido_sing="always").model_dump(mode="json")
    res = client.put(
        f"/api/bots/{bot['id']}",
        json={"name": "Uno bis", "settings": changed, "character": "tiburon"},
        headers=owner(bot),
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Uno bis" and res.json()["settings"] == changed
    assert res.json()["character"] == "tiburon"
    # Only the fields sent change; null clears the character.
    res = client.put(f"/api/bots/{bot['id']}", json={"character": None}, headers=owner(bot))
    assert res.json()["name"] == "Uno bis" and res.json()["character"] is None

    # Names stay unique, but a bot keeps its own.
    def put(b: dict, body: dict, bot_id: int | None = None) -> int:
        return client.put(f"/api/bots/{bot_id or b['id']}", json=body, headers=owner(b)).status_code

    assert put(bot, {"name": "Dos"}) == 409
    assert put(bot, {"name": "uno BIS"}) == 200
    assert put(other, {"name": "Prolijo"}) == 409
    assert put(bot, {"name": "X"}, bot_id=999) == 404
    assert put(bot, {"character": "nadie"}) == 422


def test_only_the_creator_changes_or_deletes_a_bot(client):
    settings = BotSettings().model_dump(mode="json")
    mine = client.post("/api/bots", json={"name": "Mío", "settings": settings}).json()
    theirs = client.post("/api/bots", json={"name": "Ajeno", "settings": settings}).json()
    url = f"/api/bots/{mine['id']}"
    # No token: 422. Another bot's token, or a made-up one: 403.
    assert client.put(url, json={"name": "Robado"}).status_code == 422
    assert client.delete(url).status_code == 422
    assert client.put(url, json={"name": "Robado"}, headers=owner(theirs)).status_code == 403
    assert client.delete(url, headers={"X-Bot-Token": "x"}).status_code == 403
    assert [b["name"] for b in client.get("/api/bots").json()] == ["Ajeno", "Mío"]


def test_a_bot_saved_before_tokens_can_be_played_but_not_changed(client):
    with Session(get_engine()) as db:
        db.add(BotConfig(name="Viejo", settings=BotSettings().model_dump(mode="json")))
        db.commit()
    [old] = client.get("/api/bots").json()
    assert client.delete(f"/api/bots/{old['id']}", headers={"X-Bot-Token": ""}).status_code == 403
    seats = [{"kind": "human"}] + [{"kind": "bot", "bot_id": old["id"]}] * 5
    assert client.post("/api/games", json={"mode": "strict", "seats": seats}).status_code == 201
