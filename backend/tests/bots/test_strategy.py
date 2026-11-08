import random

import pytest
from pydantic import ValidationError

from app.bots.settings import PRESETS, BotSettings, CardOrder, Policy
from app.bots.strategy import choose_action, choose_card
from app.truco.cards import Card, Suit
from app.truco.envido import EnvidoCall
from app.truco.hand import Action, ActionKind, Contest
from app.truco.match import Match, ResultKind
from app.truco.table import order_from
from tests.truco.test_hand import HANDS

K = ActionKind
rng = random.Random(0)


def c(number: int, suit: str) -> Card:
    return Card(number, Suit(suit))


def redonda() -> Contest:
    # Seat 0 holds 1 de espadas, 3 de copas, 4 de oros (tanto 4); seat 1 has tanto 31.
    return Contest(order_from(0), HANDS, pica_pica=False)


QUIET = {"envido_sing": Policy.NEVER, "truco_sing": Policy.NEVER}


# --- card order ------------------------------------------------------------------------


def test_strongest_first_then_second_then_third():
    cards = [c(4, "oro"), c(1, "espada"), c(3, "copa")]
    order = []
    while cards:
        card = choose_card(cards, [], CardOrder.STRONGEST_FIRST, rng)
        order.append(card)
        cards.remove(card)
    assert order == [c(1, "espada"), c(3, "copa"), c(4, "oro")]


def test_weakest_first():
    cards = [c(4, "oro"), c(1, "espada"), c(3, "copa")]
    assert choose_card(cards, [], CardOrder.WEAKEST_FIRST, rng) == c(4, "oro")


def test_cheapest_winner_beats_the_table_as_cheaply_as_possible():
    cards = [c(1, "espada"), c(3, "copa"), c(4, "oro")]
    assert choose_card(cards, [c(2, "oro")], CardOrder.CHEAPEST_WINNER, rng) == c(3, "copa")
    # Can't beat the 1 de espadas on the table: throw the lowest.
    hand = [c(3, "copa"), c(4, "oro")]
    assert choose_card(hand, [c(1, "espada")], CardOrder.CHEAPEST_WINNER, rng) == c(4, "oro")
    # Leading the ronda: play the strongest.
    assert choose_card(cards, [], CardOrder.CHEAPEST_WINNER, rng) == c(1, "espada")


def test_random_order_plays_one_of_the_cards():
    cards = [c(4, "oro"), c(1, "espada"), c(3, "copa")]
    seen = {choose_card(cards, [], CardOrder.RANDOM, random.Random(s)) for s in range(30)}
    assert seen == set(cards)


# --- envido ----------------------------------------------------------------------------


def test_always_starts_with_envido():
    settings = BotSettings(envido_sing=Policy.ALWAYS, truco_sing=Policy.NEVER)
    assert choose_action(redonda(), settings, rng) == Action(K.ENVIDO)


def test_configured_envido_call():
    settings = BotSettings(envido_sing=Policy.ALWAYS, envido_call=EnvidoCall.FALTA_ENVIDO)
    assert choose_action(redonda(), settings, rng) == Action(K.FALTA_ENVIDO)


def test_sings_envido_by_threshold():
    h = redonda()
    h.apply(Action.play(HANDS[0][0]))  # seat 1 (tanto 31) to act
    assert choose_action(h, BotSettings(envido_sing_threshold=31), rng) == Action(K.ENVIDO)
    assert choose_action(h, BotSettings(envido_sing_threshold=32, **QUIET), rng).kind == K.PLAY


def test_says_no_to_envido():
    h = redonda()
    h.apply(Action(K.ENVIDO))  # seat 1 (tanto 31) answers
    never = BotSettings(envido_accept=Policy.NEVER)
    assert choose_action(h, never, rng) == Action(K.NO_QUIERO)
    assert choose_action(h, BotSettings(envido_accept_threshold=31), rng) == Action(K.QUIERO)
    assert choose_action(h, BotSettings(envido_accept_threshold=32), rng) == Action(K.NO_QUIERO)


def test_raises_envido_above_its_threshold():
    h = redonda()
    h.apply(Action(K.ENVIDO))
    settings = BotSettings(envido_raise_threshold=30, envido_call=EnvidoCall.REAL_ENVIDO)
    assert choose_action(h, settings, rng) == Action(K.REAL_ENVIDO)


# --- truco -----------------------------------------------------------------------------


def test_sings_truco_with_a_strong_card():
    settings = BotSettings(envido_sing=Policy.NEVER, truco_sing_threshold=14)
    assert choose_action(redonda(), settings, rng) == Action(K.TRUCO)  # holds 1 de espadas


def test_never_sings_truco():
    settings = BotSettings(envido_sing=Policy.NEVER, truco_sing=Policy.NEVER)
    assert choose_action(redonda(), settings, rng) == Action.play(c(1, "espada"))


def test_bluffs_below_the_threshold_by_chance():
    h = redonda()
    h.apply(Action.play(HANDS[0][0]))  # seat 1: best card is a 6 (rank 3)
    settings = BotSettings(envido_sing=Policy.NEVER, truco_sing_threshold=12, bluff=1.0)
    assert choose_action(h, settings, rng) == Action(K.TRUCO)
    honest = settings.model_copy(update={"bluff": 0.0})
    assert choose_action(h, honest, rng).kind == K.PLAY


def test_accepts_or_rejects_truco():
    h = redonda()
    h.apply(Action(K.TRUCO))  # seat 1's best card is rank 3
    quiet = {"envido_sing": Policy.NEVER}
    assert choose_action(h, BotSettings(truco_accept_threshold=3, **quiet), rng) == Action(K.QUIERO)
    no = BotSettings(truco_accept_threshold=4, **quiet)
    assert choose_action(h, no, rng) == Action(K.NO_QUIERO)
    always = BotSettings(truco_accept=Policy.ALWAYS, **quiet)
    assert choose_action(h, always, rng) == Action(K.QUIERO)


def test_answers_truco_with_envido_first():
    h = redonda()
    h.apply(Action(K.TRUCO))  # seat 1 has tanto 31
    assert choose_action(h, BotSettings(envido_sing_threshold=30), rng) == Action(K.ENVIDO)


def test_raises_truco_above_its_threshold():
    h = redonda()
    h.apply(Action(K.TRUCO))
    h.apply(Action(K.QUIERO))  # team 1 accepted
    h.apply(Action.play(HANDS[0][0]))  # seat 1 to act, best card rank 3
    settings = BotSettings(envido_sing=Policy.NEVER, truco_raise_threshold=3)
    assert choose_action(h, settings, rng) == Action(K.RETRUCO)


# --- settings and full games -------------------------------------------------------------


def test_thresholds_are_validated():
    with pytest.raises(ValidationError):
        BotSettings(envido_sing_threshold=40)
    with pytest.raises(ValidationError):
        BotSettings(truco_sing_threshold=0)
    with pytest.raises(ValidationError):
        BotSettings(bluff=1.5)


# --- interactive mode ----------------------------------------------------------------


def interactive() -> Contest:
    from app.truco.config import GameConfig, RuleMode

    return Contest(
        order_from(0), HANDS, pica_pica=False, config=GameConfig(mode=RuleMode.INTERACTIVE)
    )


def test_interactive_bot_declares_its_real_tanto():
    h = interactive()
    h.apply(Action(K.ENVIDO), 0)
    assert choose_action(h, BotSettings(envido_accept_threshold=30), rng, seat=1) == Action(
        K.QUIERO
    )
    h.apply(Action(K.QUIERO), 1)
    h.apply(Action.declare(4), 0)
    assert choose_action(h, BotSettings(), rng, seat=1) == Action.declare(31)


def test_interactive_bot_says_son_buenas_when_it_cannot_win():
    h = interactive()
    h.apply(Action(K.ENVIDO), 0)
    h.apply(Action(K.QUIERO), 1)
    h.apply(Action.declare(33), 0)
    assert choose_action(h, BotSettings(), rng, seat=1) == Action(K.SON_BUENAS)


def test_interactive_bot_declares_a_tie_it_wins_by_being_closer_to_mano():
    # 11.6: seat 2 (24) stayed silent; seat 3 then declared 24. Seat 2 is closer to mano, so
    # when the turn comes back the tie is theirs and the bot declares it.
    h = interactive()
    h.apply(Action(K.ENVIDO), 0)
    h.apply(Action(K.QUIERO), 1)
    h.apply(Action.declare(20), 0)
    h.apply(Action(K.SON_BUENAS), 1)
    h.apply(Action.declare(24), 3)
    h.apply(Action(K.SON_BUENAS), 4)
    assert h.to_act == 2
    assert choose_action(h, BotSettings(), rng, seat=2) == Action.declare(24)


def test_interactive_bot_objects_to_irregular_cantos_and_accepts_pardons():
    h = interactive()
    h.apply(Action(K.VALE_CUATRO), 0)
    assert choose_action(h, BotSettings(), rng, seat=1) == Action(K.OBJETAR)

    h = interactive()
    h.apply(Action(K.TRUCO), 0)
    h.apply(Action(K.PERDON), 2)
    assert choose_action(h, BotSettings(), rng, seat=1) == Action(K.ACEPTAR_PERDON)


def test_interactive_bot_never_raises_without_the_right():
    h = interactive()
    h.apply(Action(K.TRUCO), 0)
    h.apply(Action(K.QUIERO), 1)  # team 1 holds the right to raise
    eager = BotSettings(envido_sing=Policy.NEVER, truco_raise_threshold=1)
    assert choose_action(h, eager, rng, seat=0).kind == K.PLAY


@pytest.mark.parametrize("seed", range(5))
def test_six_bots_finish_an_interactive_partido(seed):
    from app.truco.config import GameConfig, RuleMode

    game_rng = random.Random(seed)
    m = Match(rng=game_rng, config=GameConfig(mode=RuleMode.INTERACTIVE))
    bots = [PRESETS[i % len(PRESETS)].settings for i in range(6)]
    while not m.finished:
        m.deal()
        while m.hand is not None:
            seat = m.hand.to_act
            m.play(choose_action(m.hand, bots[seat], game_rng), seat)
    assert max(m.score) == 30


@pytest.mark.parametrize("seed", range(10))
def test_six_preset_bots_finish_a_partido(seed):
    game_rng = random.Random(seed)
    m = Match(rng=game_rng)
    bots = [PRESETS[i % len(PRESETS)].settings for i in range(6)]
    while not m.finished:
        m.deal()
        while m.hand is not None:
            m.play(choose_action(m.hand, bots[m.hand.to_act], game_rng))
    assert m.result.kind == ResultKind.DEPORTIVO
    assert max(m.score) == 30
