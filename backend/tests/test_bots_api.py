from app.bots.settings import BotSettings


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
    assert client.delete(f"/api/bots/{bot['id']}").status_code == 204
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
    assert client.delete("/api/bots/99").status_code == 404
