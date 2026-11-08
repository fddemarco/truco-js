from app.games.stats import PartidoLog, facts
from app.truco.cards import Card, Suit


def c(number: int, suit: str) -> Card:
    return Card(number, Suit(suit))


STRONG = [c(1, "espada"), c(1, "basto"), c(7, "espada")]  # the three best cards (Anexo A)
WEAK = [c(4, "copa"), c(4, "oro"), c(5, "basto")]
TANTO_33 = [c(7, "oro"), c(6, "oro"), c(4, "basto")]


def by_key(log: PartidoLog) -> dict:
    return {f.key: f for f in facts(log)}


def test_no_deal_no_facts():
    assert facts(PartidoLog()) == []


def test_luck_and_best_hands_come_from_the_cards_dealt():
    log = PartidoLog()
    log.deal(1, {0: STRONG, 1: WEAK, 2: TANTO_33})
    f = by_key(log)
    assert f["manos"].value == 1
    assert f["luckiest"].seat == 0 and f["unluckiest"].seat == 1
    assert f["strongest_hand"].seat == 0 and f["strongest_hand"].cards == tuple(STRONG)
    assert (f["best_tanto"].seat, f["best_tanto"].value, f["best_tanto"].mano) == (2, 33, 1)


def test_the_liar_sings_on_weak_hands_and_declares_false_numbers():
    log = PartidoLog()
    log.deal(1, {0: STRONG, 1: WEAK, 2: TANTO_33})
    log.move(0, "truco")  # strong hand: no bluff
    log.move(1, "truco")  # weak hand: bluff
    log.move(1, "envido")  # tanto 9: bluff
    log.move(2, "envido")  # 33: no bluff
    log.move(2, "declarar", 33)  # the truth
    log.move(0, "declarar", 30)  # tanto 7: a lie
    f = by_key(log)
    assert (f["liar"].seat, f["liar"].value) == (1, 2)
    assert (f["loudest"].seat, f["loudest"].value) == (1, 2)  # truco + envido


def test_counts_skip_what_nobody_did():
    log = PartidoLog()
    log.deal(1, {0: STRONG, 1: WEAK})
    log.move(1, "ronda")
    log.move(1, "envido_resuelto")
    f = by_key(log)
    assert f["rondas"].seat == 1 and f["envido_king"].seat == 1
    assert "prudent" not in f and "liar" not in f
