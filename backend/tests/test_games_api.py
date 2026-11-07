from app.bots.settings import BotSettings

BOT = {"kind": "bot", "bot_preset": "prolijo"}
HUMAN = {"kind": "human"}
PRIORITY = [
    "jugar",
    "quiero",
    "declarar",
    "son_buenas",
    "aceptar_perdon",
    "objetar",
    "no_quiero",
]


def create(client, seats, mode="strict") -> str:
    res = client.post("/api/games", json={"mode": mode, "seats": seats})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def join(client, game, seat, name="") -> str:
    res = client.post(f"/api/games/{game}/join", json={"seat": seat, "name": name})
    assert res.status_code == 200, res.text
    return res.json()["token"]


def view(client, game, token=None) -> dict:
    params = {"token": token} if token else {}
    return client.get(f"/api/games/{game}", params=params).json()


def pick(actions: list[dict]) -> dict:
    for kind in PRIORITY:
        for action in actions:
            if action["kind"] == kind:
                return action
    raise AssertionError(f"nothing to play in {actions}")


def play_until_the_end(client, game, token) -> dict:
    v = view(client, game, token)
    for _ in range(3000):
        if v["result"]:
            return v
        if v["can_deal"]:
            v = client.post(f"/api/games/{game}/deal", json={"token": token}).json()
            continue
        assert v["to_act"] == v["me"], "bots should have played until it is our turn"
        res = client.post(
            f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])}
        )
        assert res.status_code == 200, res.text
        v = res.json()
    raise AssertionError("the partido didn't end")


def test_one_human_against_bots_plays_a_full_partido(client):
    game = create(client, [{**HUMAN, "name": "Ana"}] + [BOT] * 5)
    token = join(client, game, 0)
    v = view(client, game, token)
    assert v["started"] and v["me"] == 0
    assert len(v["my_cards"]) == 3
    assert v["seats"][0]["name"] == "Ana" and v["seats"][1]["name"] == "Prolijo"
    end = play_until_the_end(client, game, token)
    assert max(end["score"]) == 30
    assert end["result"]["winner"] in (0, 1)
    assert any(e["kind"] == "fin_mano" for e in end["events"])


def test_interactive_partido_with_bots(client):
    game = create(client, [HUMAN] + [BOT] * 5, mode="interactive")
    token = join(client, game, 0)
    end = play_until_the_end(client, game, token)
    assert max(end["score"]) == 30


def test_game_waits_for_every_human_seat(client):
    game = create(client, [HUMAN, HUMAN] + [BOT] * 4)
    first = join(client, game, 0, "Ana")
    assert not view(client, game, first)["started"]
    bad = client.post(f"/api/games/{game}/act", json={"token": first, "action": {"kind": "quiero"}})
    assert bad.status_code == 400
    second = join(client, game, 1, "Beto")
    assert view(client, game, first)["started"]
    # Each token only sees its own seat's cards.
    a, b = view(client, game, first), view(client, game, second)
    assert a["me"] == 0 and b["me"] == 1
    assert a["my_cards"] != b["my_cards"]
    assert view(client, game)["my_cards"] == []  # spectators see no cards


def test_seats_can_only_be_joined_once_and_bots_never(client):
    game = create(client, [HUMAN] + [BOT] * 5)
    join(client, game, 0)
    taken = client.post(f"/api/games/{game}/join", json={"seat": 0})
    assert taken.status_code == 409
    assert client.post(f"/api/games/{game}/join", json={"seat": 1}).status_code == 409


def test_unknown_game_or_token(client):
    assert client.get("/api/games/nope").status_code == 404
    game = create(client, [HUMAN] + [BOT] * 5)
    join(client, game, 0)
    assert client.get(f"/api/games/{game}", params={"token": "x"}).status_code == 403


def test_illegal_move_is_rejected(client):
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    v = view(client, game, token)
    assert v["to_act"] == 0  # bots never play past a human's turn
    mine = {(c["number"], c["suit"]) for c in v["my_cards"]}
    other = next(
        {"number": n, "suit": s}
        for n in (1, 2, 3, 4, 5, 6, 7, 10, 11, 12)
        for s in ("espada", "basto", "oro", "copa")
        if (n, s) not in mine
    )
    res = client.post(
        f"/api/games/{game}/act",
        json={"token": token, "action": {"kind": "jugar", "card": other}},
    )
    assert res.status_code == 400


def test_bots_answer_right_away(client):
    seats = [HUMAN] + [{"kind": "bot", "bot_preset": "cauteloso"}] * 5
    game = create(client, seats)
    token = join(client, game, 0)
    v = view(client, game, token)
    while v["to_act"] != 0 or not any(a["kind"] == "truco" for a in v["actions"]):
        if v["can_deal"]:
            v = client.post(f"/api/games/{game}/deal", json={"token": token}).json()
        else:
            v = client.post(
                f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])}
            ).json()
    v = client.post(
        f"/api/games/{game}/act", json={"token": token, "action": {"kind": "truco"}}
    ).json()
    answered = [e for e in v["events"] if e["kind"] in ("quiero", "no_quiero")]
    assert answered and answered[-1]["seat"] % 2 == 1


def test_games_with_saved_bots(client):
    settings = BotSettings(envido_sing="always").model_dump(mode="json")
    bot = client.post("/api/bots", json={"name": "Mío", "settings": settings}).json()
    game = create(client, [HUMAN] + [{"kind": "bot", "bot_id": bot["id"]}] * 5)
    assert view(client, game)["seats"][1]["name"] == "Mío"
    missing = client.post(
        "/api/games", json={"seats": [HUMAN] + [{"kind": "bot", "bot_id": 999}] * 5}
    )
    assert missing.status_code == 422
    unknown = client.post(
        "/api/games", json={"seats": [HUMAN] + [{"kind": "bot", "bot_preset": "x"}] * 5}
    )
    assert unknown.status_code == 422
    assert client.post("/api/games", json={"seats": [BOT] * 6}).status_code == 422


def test_senas_only_in_interactive_mode(client):
    sena = {"sena": "sena_05", "spot": "labio_inferior", "duration_ms": 500}
    strict = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, strict, 0)
    assert (
        client.post(f"/api/games/{strict}/sena", json={"token": token, **sena}).status_code == 400
    )

    game = create(client, [HUMAN] + [BOT] * 5, mode="interactive")
    token = join(client, game, 0)
    res = client.post(f"/api/games/{game}/sena", json={"token": token, **sena})
    assert res.status_code == 200, res.text
    assert res.json()["senas"][0]["seat"] == 0
    wrong = {**sena, "spot": "nariz"}
    assert client.post(f"/api/games/{game}/sena", json={"token": token, **wrong}).status_code == 400
