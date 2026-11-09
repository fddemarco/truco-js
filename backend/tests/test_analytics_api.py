"""GET /api/analytics/win-rates: filters, hand lookup, order and pagination."""

import pytest
from experiments import win_rates as w

from app.bots.settings import CardOrder
from app.truco.config import Format

PP, RD = Format.PICA_PICA, Format.REDONDA


def strength(*rates):
    return w.Strength([w.Tally(r, 1) for r in rates])


@pytest.fixture
def rows(data_dir):
    w.store(
        [
            w.row(PP, "envido", None, strength(0.9, 0.8), tanto=28),  # 0.85
            w.row(PP, "envido", None, strength(0.2, 0.0), tanto=4),  # 0.1
        ],
        PP,
        "envido",
        None,
    )
    w.store([w.row(RD, "envido", None, strength(*[0.7] * 6), tanto=28)], RD, "envido", None)  # 0.7
    w.store(
        [
            w.row(RD, "truco", "random", strength(*[0.6] * 6), ranks=(14, 12, 1)),  # 0.6
            w.row(RD, "truco", "random", strength(*[0.3] * 6), ranks=(1, 2, 3)),  # 0.3
        ],
        RD,
        "truco",
        "random",
    )


def get(client, **params):
    response = client.get("/api/analytics/win-rates", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_lists_everything_strongest_first(client, rows):
    page = get(client)
    assert page["total"] == 5
    assert [i["strength"] for i in page["items"]] == [0.85, 0.7, 0.6, 0.3, 0.1]
    top = page["items"][0]
    assert top["format"] == "pica_pica" and top["tanto"] == 28 and top["ranks"] is None
    assert top["by_seat"] == [0.9, 0.8] and top["exact"] is True
    assert page["items"][2]["ranks"] == [14, 12, 1] and len(page["items"][2]["by_seat"]) == 6


def test_filters(client, rows):
    assert get(client, format="redonda")["total"] == 3
    assert get(client, format="redonda", canto="envido")["total"] == 1
    assert get(client, policy="random")["total"] == 2
    assert get(client, policy=CardOrder.CHEAPEST_WINNER)["total"] == 0
    assert get(client, tanto=28)["total"] == 2
    assert get(client, min_strength=0.3, max_strength=0.7)["total"] == 3


def test_hand_finds_its_tanto_and_ranks(client, rows):
    """1e (14), 7e (12), 4c (1): tanto 28, ranks 14-12-1, whatever the order given."""
    page = get(client, hand=["4-copa", "1-espada", "7-espada"], format="redonda")
    assert [(i["canto"], i["tanto"], i["ranks"]) for i in page["items"]] == [
        ("envido", 28, None),
        ("truco", None, [14, 12, 1]),
    ]


def test_order_and_pages(client, rows):
    page = get(client, descending=False, limit=2, offset=1)
    assert page["total"] == 5
    assert [i["strength"] for i in page["items"]] == [0.3, 0.6]


@pytest.mark.parametrize(
    "params",
    [
        {"hand": "1-copas"},
        {"hand": "8-oro"},
        {"hand": ["1-espada", "7-espada"]},
        {"hand": ["1-espada", "1-espada", "7-espada"]},
        {"format": "reglamentos"},
        {"canto": "flor"},
        {"policy": "best"},
        {"limit": 501},
        {"min_strength": 1.5},
    ],
)
def test_rejects_bad_filters(client, params):
    assert client.get("/api/analytics/win-rates", params=params).status_code == 422
