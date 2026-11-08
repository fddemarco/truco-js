from app.bots.settings import BotSettings
from app.truco.cards import Card, Suit
from app.truco.envido import tanto

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


def deal(client, game, token) -> dict:
    res = client.post(f"/api/games/{game}/deal", json={"token": token})
    assert res.status_code == 200, res.text
    return res.json()


def view(client, game, token=None) -> dict:
    params = {"token": token} if token else {}
    return client.get(f"/api/games/{game}", params=params).json()


def my_turn(client, game, token) -> dict:
    """The view once a mano waits on this seat.

    Bots can settle a mano before the human acts (a rival bot may answer a bot's truco, 10.1),
    so deal on until it is our turn, as a player at the table would.
    """
    v = view(client, game, token)
    for _ in range(50):
        if v["to_act"] == v["me"]:
            return v
        assert v["can_deal"], "bots should have played until it is our turn"
        v = client.post(f"/api/games/{game}/deal", json={"token": token}).json()
    raise AssertionError("never our turn")


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
    v = my_turn(client, game, token)
    assert v["started"] and v["me"] == 0
    assert len(v["my_cards"]) == 3
    # A bot plays as its character.
    assert v["seats"][0]["name"] == "Ana" and v["seats"][1]["name"] == "Maníaca"
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
    started = view(client, game, first)
    # The table shuffles, cuts and deals the first mano like every other one.
    assert started["started"] and started["can_deal"]
    assert started["my_cards"] == [] and started["events"] == []
    deal(client, game, second)
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
    v = my_turn(client, game, token)  # bots never play past a human's turn
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
    my_turn(client, game, token)  # señas need a mano in progress
    res = client.post(f"/api/games/{game}/sena", json={"token": token, **sena})
    assert res.status_code == 200, res.text
    assert res.json()["senas"][0]["seat"] == 0
    wrong = {**sena, "spot": "nariz"}
    assert client.post(f"/api/games/{game}/sena", json={"token": token, **wrong}).status_code == 400
    # C.3: 08–10 (figures) and 11 (no truco cards) are not valid señas.
    for gone in (
        {"sena": "sena_08", "spot": "muneca_derecha"},
        {"sena": "sena_11", "spot": "ojos"},
    ):
        res = client.post(f"/api/games/{game}/sena", json={"token": token, **sena, **gone})
        assert res.status_code == 422


def test_a_seat_only_sees_the_senas_of_the_player_across_it_looks_at(client):
    # 14.4 / Anexo C: señas are only seen face to face, so a seat sees just the player across
    # its camera is on. Seat 0 (side 0) looks across at 5, 4 or 3; seat 1 is beside it.
    game = create(client, [HUMAN] * 3 + [BOT, HUMAN, BOT], mode="interactive")
    tokens = {s: join(client, game, s) for s in (0, 1, 2, 4)}
    first = deal(client, game, tokens[0])
    assert first["started"] and first["hand_kind"] != "pica_pica"  # every seat may signal
    sena = {"sena": "sena_05", "spot": "labio_inferior", "duration_ms": 3000}

    def make(seat):
        res = client.post(f"/api/games/{game}/sena", json={"token": tokens[seat], **sena})
        return res.status_code

    def seen_by(seat, look=None):
        params = {"token": tokens[seat]} | ({"look": look} if look is not None else {})
        return {s["seat"] for s in client.get(f"/api/games/{game}", params=params).json()["senas"]}

    assert make(4) == 200 and make(1) == 200
    assert seen_by(0, look=4) == {4}
    assert seen_by(0, look=5) == set()  # looking at someone else
    assert seen_by(0) == set()  # the default look is straight across: seat 5
    assert 1 not in seen_by(0, look=1)  # beside, never visible, even if asked
    assert seen_by(1) == {1, 4}  # its own, and 4 straight across
    assert {1, 4} <= {s["seat"] for s in view(client, game)["senas"]}  # spectators see all


def test_played_cards_stay_on_the_table_per_seat(client):
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    v = my_turn(client, game, token)
    # Answer whatever blocks play (a truco from a bot...) until a card can be played.
    while not any(a["kind"] == "jugar" for a in v["actions"]):
        v = client.post(
            f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])}
        ).json()
        v = my_turn(client, game, token)
    before = {s["seat"]: len(s["played"]) for s in v["seats"]}
    card = next(a for a in v["actions"] if a["kind"] == "jugar")
    v = client.post(f"/api/games/{game}/act", json={"token": token, "action": card}).json()
    mine = v["seats"][0]["played"]
    assert len(mine) == before[0] + 1 and mine[-1] == card["card"]
    total = sum(len(s["played"]) for s in v["seats"])
    assert total == sum(len(r) for r in v["rounds"]) or v["hand_kind"] == "pica_pica"


def test_each_closed_ronda_is_announced(client):
    # 7: once the cards of a ronda are down, an event names its winning seat (none: parda).
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    seen: list[dict] = []
    v = view(client, game, token)
    for _ in range(3000):
        seen += v["events"]
        if v["result"]:
            break
        if v["can_deal"]:
            v = client.post(f"/api/games/{game}/deal", json={"token": token}).json()
        else:
            v = client.post(
                f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])}
            ).json()
    rondas = [e for e in seen if e["kind"] == "ronda"]
    assert rondas  # a whole partido closes rondas
    for e in rondas:
        assert e["number"] in (1, 2, 3)
        assert e["seat"] is None or 0 <= e["seat"] < 6


def test_view_carries_the_phase_of_the_mano_and_the_partido(client):
    game = create(client, [HUMAN] * 6)
    assert view(client, game)["match_phase"] == "dealing"
    assert view(client, game)["phase"] is None
    tokens = [join(client, game, s) for s in range(6)]
    assert view(client, game)["match_phase"] == "dealing"  # until the table deals
    v = deal(client, game, tokens[0])
    assert (v["match_phase"], v["phase"]) == ("in_hand", "playing")
    seat = v["to_act"]
    res = client.post(
        f"/api/games/{game}/act", json={"token": tokens[seat], "action": {"kind": "truco"}}
    )
    v = res.json()
    assert v["phase"] == "answering" and v["to_act"] == (seat + 1) % 6


def test_characters_are_never_repeated_and_choices_are_kept(client):
    seats = [{**HUMAN, "character": "roca"}, {**BOT, "character": "roca"}] + [BOT] * 4
    game = create(client, seats)
    v = view(client, game)
    characters = [s["character"] for s in v["seats"]]
    assert characters[0] == "roca"
    assert len(set(characters)) == 6
    assert v["seats"][1]["name"] == "Maníaca"  # lost "roca": took a free one, and its name


def test_saved_bots_keep_their_name_and_character(client):
    settings = BotSettings().model_dump(mode="json")
    bot = client.post(
        "/api/bots", json={"name": "Doña Rosa", "settings": settings, "character": "novato"}
    ).json()
    saved = {"kind": "bot", "bot_id": bot["id"]}
    game = create(client, [HUMAN, saved] + [BOT] * 4)
    seat = view(client, game)["seats"][1]
    assert (seat["name"], seat["character"]) == ("Doña Rosa", "novato")


def test_team_names_are_drawn_or_given(client):
    drawn = view(client, create(client, [HUMAN] + [BOT] * 5))["team_names"]
    assert len(drawn) == 2 and drawn[0] != drawn[1]
    res = client.post(
        "/api/games",
        json={"seats": [HUMAN] + [BOT] * 5, "team_names": [" Los Leones ", "Las Liebres"]},
    )
    assert view(client, res.json()["id"])["team_names"] == ["Los Leones", "Las Liebres"]
    bad = client.post("/api/games", json={"seats": [HUMAN] + [BOT] * 5, "team_names": ["Solo"]})
    assert bad.status_code == 422


def test_view_names_the_mano_and_the_pie(client):
    game = create(client, [HUMAN] + [BOT] * 5)
    v = my_turn(client, game, join(client, game, 0))
    if v["hand_kind"] == "redonda":
        # The mano is right of the dealer; the pie is the dealer (5.6).
        assert v["mano"] == (v["dealer"] + 1) % 6 and v["pie"] == v["dealer"]
    else:
        assert {v["mano"], v["pie"]} == set(v["duel"])


def test_each_move_is_a_step_with_the_table_as_the_viewer_saw_it(client):
    # Bots play right after the deal, so one response carries several moves; each comes with
    # the table right after it, so the client can show them one at a time.
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    start = view(client, game, token)["step"]
    v = client.post(f"/api/games/{game}/deal", json={"token": token, "since": start}).json()
    steps = v["steps"]
    assert steps[0]["events"][0]["kind"] == "reparto" and steps[0]["seat"] is None
    # The new hand is on the table from the deal on, not from the viewer's turn.
    assert len(steps[0]["view"]["my_cards"]) == 3
    assert steps[0]["view"]["seats"][0]["played"] == []
    for before, after in zip(steps, steps[1:], strict=False):
        assert after["index"] == before["index"] + 1
    for s in steps[1:]:
        assert s["seat"] != 0  # only bots moved
        card = next((e["card"] for e in s["events"] if e["kind"] == "jugar"), None)
        if card:
            assert card in s["view"]["seats"][s["seat"]]["played"]
    assert steps[-1]["index"] == v["step"]
    # Asking again from the latest step: nothing new.
    again = client.get(f"/api/games/{game}", params={"token": token, "since": v["step"]})
    assert again.json()["steps"] == []


def test_arriving_replays_the_mano_since_the_viewers_last_move(client):
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    v = my_turn(client, game, token)
    arrived = view(client, game, token)  # no `since`: arriving at the table
    replay = arrived["steps"]
    if replay:  # bots played before our turn
        assert replay[0]["events"][0]["kind"] == "reparto"
        base = arrived["base"]  # the table waiting for this mano's deal
        assert base["can_deal"] and base["hand_number"] == arrived["hand_number"] - 1
    # After our own move, arriving again replays only what came after it.
    res = client.post(f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])})
    assert res.status_code == 200
    after = view(client, game, token)
    assert all(s["seat"] != 0 for s in after["steps"])
    if after["steps"]:
        assert after["base"] is not None
    # Spectators get steps too, without anyone's cards.
    watched = client.get(f"/api/games/{game}", params={"since": -1}).json()["steps"]
    assert watched and all(s["view"]["my_cards"] == [] for s in watched)


# --- scoring: target and canto chains -----------------------------------------------------


def test_scoring_info_lists_chains_with_the_reglamento_points(client):
    info = client.get("/api/games/scoring").json()
    assert info["target"] == 30
    chains = {tuple(c["chain"]): c for c in info["chains"]}
    assert chains[("envido", "real_envido")]["quiero"] == 5
    assert chains[("envido", "real_envido")]["no_quiero"] == 2
    assert chains[("falta_envido",)]["quiero"] is None  # what the leader lacks
    assert chains[("truco", "retruco")]["family"] == "truco"


def test_game_with_custom_scoring_shows_its_target(client):
    body = {
        "seats": [HUMAN] + [BOT] * 5,
        "scoring": {"target": 18, "chains": [{"chain": ["truco"], "quiero": 3}]},
    }
    res = client.post("/api/games", json=body)
    assert res.status_code == 201, res.text
    v = view(client, res.json()["id"])
    assert v["target"] == 18 and v["malas_max"] == 9


def test_default_game_plays_to_30(client):
    v = view(client, create(client, [HUMAN] + [BOT] * 5))
    assert v["target"] == 30 and v["malas_max"] == 15


def test_scoring_errors_are_422(client):
    seats = [HUMAN] + [BOT] * 5
    for scoring in (
        {"target": 5},
        {"chains": [{"chain": ["envido", "truco"], "quiero": 2}]},
        {"chains": [{"chain": ["truco"], "quiero": 2}, {"chain": ["truco"], "no_quiero": 1}]},
    ):
        res = client.post("/api/games", json={"seats": seats, "scoring": scoring})
        assert res.status_code == 422, scoring


def test_view_tells_each_player_their_real_tanto(client):
    # The tanto counts the three cards dealt (11.1), so the UI can offer it when declaring.
    game = create(client, [HUMAN, BOT, BOT, BOT, BOT, BOT], mode="interactive")
    token = join(client, game, 0)
    v = my_turn(client, game, token)
    cards = [Card(c["number"], Suit(c["suit"])) for c in v["my_cards"]]
    assert v["my_tanto"] == tanto(cards)
    assert view(client, game)["my_tanto"] is None  # spectators see no tanto


def test_strict_envido_is_told_as_the_table_hears_it(client):
    # Strict resolves the envido from the real tantos; the table hears it in turn (11.4,
    # 11.5): declarations, then who won it with which tanto, for every viewer.
    game = create(client, [HUMAN] + [BOT] * 5)
    token = join(client, game, 0)
    v = view(client, game, token)
    seen_stakes = seen_result = False
    for _ in range(3000):
        if v["result"] or (seen_stakes and seen_result):
            break
        if v["envido_stakes"]:
            stakes = v["envido_stakes"]
            assert stakes["no_quiero"] >= 1 and min(stakes["quiero"]) >= 2
            seen_stakes = True
        events = v["events"]
        for i, e in enumerate(events):
            if e["kind"] == "envido_resuelto" and e["number"] is not None:
                before = events[:i]
                said = [b for b in before if b["kind"] in ("declarar", "son_buenas")]
                assert any(b["seat"] == e["seat"] and b["number"] == e["number"] for b in said)
                seen_result = True
        if v["can_deal"]:
            v = deal(client, game, token)
            continue
        v = client.post(
            f"/api/games/{game}/act", json={"token": token, "action": pick(v["actions"])}
        ).json()
    assert seen_result, "no envido querido in a whole partido"
    assert seen_stakes, "never asked to answer an envido"
