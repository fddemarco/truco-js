"""Configurable scoring (app/truco/scoring.py): target and points per canto chain.

The defaults are the reglamento (1.3–1.5, 11.9, 12.2, 15.1, Anexo B). Applies to both modes:
each rule is checked in strict and in interactive.
"""

import random

import pytest

from app.truco.config import GameConfig, RuleMode
from app.truco.envido import EnvidoCall
from app.truco.hand import Action, ActionKind, Contest
from app.truco.match import HandKind, Match, ResultKind
from app.truco.scoring import (
    REGLAMENTO,
    ChainPoints,
    Scoring,
    ScoringError,
    chain_family,
    envido_chains,
    truco_chains,
)
from app.truco.table import order_from
from app.truco.truco import TrucoCall
from tests.truco.test_hand import HANDS
from tests.truco.test_match import concede

K = ActionKind
MODES = [RuleMode.STRICT, RuleMode.INTERACTIVE]
E, R, F = EnvidoCall
T, RT, V = TrucoCall


def contest(mode: RuleMode, scoring: Scoring, scores=(0, 0)) -> Contest:
    config = GameConfig(mode=mode, scoring=scoring)
    return Contest(order_from(0), HANDS, pica_pica=False, scores=scores, config=config)


def act(h: Contest, kind: ActionKind) -> None:
    h.apply(Action(kind), h.to_act)


def play_out(h: Contest) -> None:
    while not h.finished:
        seat = h.to_act
        h.apply(Action.play(h.hands[seat][0]), seat)


# --- chains ------------------------------------------------------------------------------


def test_chains_stay_within_one_canto_family():
    assert chain_family(["envido", "real_envido"]) == "envido"
    assert chain_family(["retruco"]) == "truco"
    assert chain_family(["truco", "vale_cuatro"]) == "truco"
    assert chain_family(["envido", "truco"]) is None  # families never mix
    assert chain_family(["real_envido", "envido"]) is None  # not a valid sequence (B.2)
    assert chain_family(["retruco", "truco"]) is None  # truco only climbs
    assert chain_family([]) is None


def test_every_listed_chain_is_valid_and_listed_once():
    chains = envido_chains() + truco_chains()
    assert len(chains) == len(set(chains))
    assert all(chain_family(c) for c in chains)
    assert len(envido_chains()) == 11 and len(truco_chains()) == 7


def test_a_chain_defined_twice_is_rejected():
    with pytest.raises(ScoringError, match="twice"):
        Scoring.build(30, [(["truco"], ChainPoints(3)), (["truco"], ChainPoints(4))])


@pytest.mark.parametrize(
    "target, chains",
    [
        (5, {}),
        (61, {}),
        (30, {("envido", "truco"): ChainPoints(1)}),
        (30, {("truco",): ChainPoints(-1)}),
    ],
)
def test_invalid_scoring_is_rejected(target, chains):
    with pytest.raises(ScoringError):
        Scoring(target, chains)


# --- defaults: the reglamento ------------------------------------------------------------


def test_defaults_are_the_reglamento():
    s = REGLAMENTO
    assert s.target == 30 and s.malas_max == 15 and s.pica_pica_until == 25
    assert [s.truco_quiero(LADDER) for LADDER in ([], [T], [T, RT], [T, RT, V])] == [1, 2, 3, 4]
    assert s.truco_no_quiero([T, RT], [T]) == 2  # 12.2
    pts = dict(pica_pica=False, scores=(0, 0), winner=0)
    assert s.envido_points([E, R], True, **pts) == 5
    assert s.envido_points([E, R], False, **pts) == 2  # B.3
    assert s.envido_points([F], False, **pts) == 1


# --- truco chains (12.2) -----------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_configured_truco_quiero(mode):
    h = contest(mode, Scoring(30, {("truco",): ChainPoints(quiero=3)}))
    act(h, K.TRUCO)
    act(h, K.QUIERO)
    play_out(h)
    assert h.points == [3, 0]


@pytest.mark.parametrize("mode", MODES)
def test_configured_truco_no_quiero(mode):
    h = contest(mode, Scoring(30, {("truco",): ChainPoints(no_quiero=2)}))
    act(h, K.TRUCO)
    act(h, K.NO_QUIERO)
    assert h.points == [2, 0]


@pytest.mark.parametrize("mode", MODES)
def test_truco_retruco_chain_is_not_retruco_alone(mode):
    scoring = Scoring(
        30, {("truco", "retruco"): ChainPoints(quiero=5), ("retruco",): ChainPoints(9)}
    )
    h = contest(mode, scoring)
    act(h, K.TRUCO)
    act(h, K.RETRUCO)  # raising as an answer accepts truco
    act(h, K.QUIERO)
    play_out(h)
    assert sorted(h.points) == [0, 5]


def test_an_unobjected_jump_scores_as_its_own_chain():
    # Interactive only: a retruco with no truco before is irregular, but answered it stands.
    scoring = Scoring(
        30, {("retruco",): ChainPoints(quiero=7), ("truco", "retruco"): ChainPoints(5)}
    )
    h = contest(RuleMode.INTERACTIVE, scoring)
    h.apply(Action(K.RETRUCO), 0)
    h.apply(Action(K.QUIERO), 1)
    play_out(h)
    assert h.points == [7, 0]


@pytest.mark.parametrize("mode", MODES)
def test_unconfigured_no_quiero_is_what_was_querido(mode):
    # Truco querido is worth 4 here; retruco not querido gives that, not the reglamento's 2.
    h = contest(mode, Scoring(30, {("truco",): ChainPoints(quiero=4)}))
    act(h, K.TRUCO)
    act(h, K.QUIERO)
    play_out_until_turn(h, team=1)
    act(h, K.RETRUCO)
    act(h, K.NO_QUIERO)
    assert h.points == [0, 4]


def play_out_until_turn(h: Contest, team: int) -> None:
    while h.to_act % 2 != team:
        seat = h.to_act
        h.apply(Action.play(h.hands[seat][0]), seat)


@pytest.mark.parametrize("mode", MODES)
def test_leaving_with_a_truco_pending_scores_its_no_quiero(mode):
    h = contest(mode, Scoring(30, {("truco",): ChainPoints(no_quiero=3)}))
    act(h, K.TRUCO)
    h.apply(Action(K.NOS_VAMOS), 1)  # 8.5: pending cantos count as rejected
    assert h.points == [3, 0]


# --- envido chains (Anexo B) -------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_configured_envido_chain(mode):
    scoring = Scoring(30, {("envido", "real_envido"): ChainPoints(quiero=8, no_quiero=4)})
    h = contest(mode, scoring)
    act(h, K.ENVIDO)
    act(h, K.REAL_ENVIDO)
    act(h, K.NO_QUIERO)
    assert h.points == [0, 4]
    assert scoring.envido_points([E, R], True, pica_pica=False, scores=(0, 0), winner=0) == 8
    # Real envido alone is another chain: still the reglamento's.
    assert scoring.envido_points([R], True, pica_pica=False, scores=(0, 0), winner=0) == 3


@pytest.mark.parametrize("mode", MODES)
def test_envido_no_quiero_defaults_to_the_configured_prefix(mode):
    h = contest(mode, Scoring(30, {("envido",): ChainPoints(quiero=3)}))
    act(h, K.ENVIDO)
    act(h, K.REAL_ENVIDO)
    act(h, K.NO_QUIERO)
    assert h.points == [0, 3]


def test_falta_envido_follows_the_target():
    s = Scoring(20)
    pts = dict(pica_pica=False, winner=0)
    assert s.envido_points([F], True, scores=(4, 8), **pts) == 16  # both in malas (≤ 10)
    assert s.envido_points([F], True, scores=(4, 12), **pts) == 8  # what the leader lacks
    assert s.envido_points([F], True, scores=(4, 12), pica_pica=True, winner=0) == 6


# --- target (1.3–1.5, 15.1) --------------------------------------------------------------


@pytest.mark.parametrize("mode", MODES)
def test_a_shorter_partido_ends_at_its_target(mode):
    config = GameConfig(mode=mode, scoring=Scoring(15))
    m = Match(first_dealer=5, rng=random.Random(1), config=config)
    m.score = [0, 14]
    m.deal()
    m.play(Action(K.TRUCO), 0)
    m.play(Action(K.QUIERO), 1)
    m.play(Action(K.NOS_VAMOS), 0)
    assert m.score == [0, 15]  # capped at the target
    assert m.result.kind == ResultKind.DEPORTIVO and m.result.winner == 1


@pytest.mark.parametrize("mode", MODES)
def test_pica_pica_stops_as_close_to_the_target_as_25_is_to_30(mode):
    config = GameConfig(mode=mode, scoring=Scoring(20))
    m = Match(first_dealer=0, rng=random.Random(1), config=config)
    m.score = [4, 0]
    m.deal()
    concede(m)
    assert m.next_hand_kind() == HandKind.PICA_PICA
    m.score = [15, 0]
    assert m.next_hand_kind() == HandKind.REDONDA
