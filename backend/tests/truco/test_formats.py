"""Partido formats (GameConfig.format), each played in both rule modes.

- redonda: three against three, every mano redonda (no pica-pica, 15.1 does not apply).
- pica_pica: one against one, every mano a single duelo between seats 0 and 1.
"""

import random

import pytest

from app.truco.config import Format, GameConfig, RuleMode
from app.truco.envido import tanto
from app.truco.hand import Action, ActionKind, Contest
from app.truco.match import HandKind, Match, MatchError
from app.truco.scoring import REGLAMENTO
from app.truco.signals import BodySpot, Sena, SenaEvent

K = ActionKind
MODES = [RuleMode.STRICT, RuleMode.INTERACTIVE]


def match(fmt: Format, mode: RuleMode, dealer: int = 0) -> Match:
    return Match(first_dealer=dealer, rng=random.Random(3), config=GameConfig(mode, format=fmt))


def kinds(m: Match, seat: int) -> set[ActionKind]:
    return {a.kind for a in m.actions_for(seat)}


@pytest.mark.parametrize("mode", MODES)
def test_redonda_never_plays_pica_pica(mode):
    m = match(Format.REDONDA, mode)
    m.score = [12, 7]  # past 5 (15.1): the reglamento would alternate with pica-pica now
    m.pica_pica_started = True
    for _ in range(3):
        assert m.next_hand_kind() == HandKind.REDONDA
        hand = m.deal()
        assert isinstance(hand, Contest) and len(hand.seats) == 6
        m.play(Action(K.NOS_VAMOS))
    assert m.history[-1].kind == HandKind.REDONDA


@pytest.mark.parametrize("mode", MODES)
def test_pica_pica_is_one_against_one(mode):
    m = match(Format.PICA_PICA, mode, dealer=1)
    hand = m.deal()
    assert m.hand_kind == HandKind.PICA_PICA
    assert isinstance(hand, Contest) and hand.seats == [0, 1]  # mano: right of the dealer (5.5)
    assert len(hand.hands[0]) == len(hand.hands[1]) == 3
    # No partners: no "nos vamos al mazo" and no señas.
    moves = kinds(m, 0)
    assert K.MAZO in moves
    assert K.NOS_VAMOS not in moves and K.SENA not in moves
    m.play(Action(K.MAZO), 0)
    assert m.score == [0, 1]
    assert m.dealer == 0  # the deck goes round the two of them (5.7)
    assert m.deal().seats == [1, 0]


@pytest.mark.parametrize("mode", MODES)
def test_pica_pica_partido_is_played_to_the_target(mode):
    m = match(Format.PICA_PICA, mode)
    m.score = [27, 0]
    while not m.finished:
        hand = m.deal()
        if hand.to_act == 0:  # strict: seat 1 leaves in turn
            m.play(Action.play(hand.hands[0][0]), 0)
        m.play(Action(K.MAZO), 1)  # seat 1 leaves every mano: seat 0 gets to 30
    assert m.result.winner == 0 and max(m.score) == 30


@pytest.mark.parametrize("mode", MODES)
def test_pica_pica_falta_envido_is_what_the_leader_lacks(mode):
    # Inside a pica-pica mano a duelo's falta envido is 6; a whole partido one against one
    # scores it like a mano redonda (11.3).
    m = match(Format.PICA_PICA, mode)
    m.score = [3, 1]
    hand = m.deal()
    mano = hand.to_act
    m.play(Action(K.FALTA_ENVIDO), mano)
    m.play(Action(K.QUIERO), 1 - mano)
    while hand.envido is None:  # interactive: each says their real tanto, or son buenas
        seat = hand.to_act
        truth = Action.declare(tanto(hand.dealt[seat]))
        m.play(truth if truth in m.actions_for(seat) else Action(K.SON_BUENAS), seat)
    envido = hand.envido
    assert envido.accepted
    expected = REGLAMENTO.envido_points(
        ["falta_envido"], True, pica_pica=False, scores=(3, 1), winner=envido.team
    )
    assert expected != 6 and envido.points == expected


def test_no_senas_one_against_one():
    m = match(Format.PICA_PICA, RuleMode.INTERACTIVE)
    m.deal()
    with pytest.raises(MatchError):
        m.sena(SenaEvent(0, Sena.TRES, BodySpot.LABIO_INFERIOR, 0, 500))
