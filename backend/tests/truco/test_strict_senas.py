import random

from app.truco.config import GameConfig
from app.truco.hand import Action, ActionKind, Contest
from app.truco.signals import Sena
from app.truco.table import order_from
from tests.truco.test_hand import HANDS

K = ActionKind


def redonda(p: float, q: float, seed: int = 0) -> Contest:
    config = GameConfig(sena_notice_p=p, sena_leak_q=q)
    return Contest(order_from(0), HANDS, pica_pica=False, config=config, rng=random.Random(seed))


def has_sena(contest: Contest) -> bool:
    return any(a.kind == K.SENA for a in contest.legal_actions())


def test_sena_is_a_free_action_once_per_turn():
    h = redonda(1, 0)
    assert has_sena(h)
    h.apply(Action.signal(Sena.ANCHO_DE_ESPADAS))
    assert h.to_act == 0  # the turn is not used up
    assert not has_sena(h)
    h.apply(Action.play(HANDS[0][0]))
    assert h.to_act == 1 and has_sena(h)


def test_only_the_player_to_act_can_signal():
    h = redonda(1, 0)
    assert h.actions_for(3) == []


def test_teammates_notice_and_rivals_detect_by_chance():
    h = redonda(1, 0)
    h.apply(Action.signal(Sena.TRES))
    assert [s.sena for s in h.senas_seen(2)] == [Sena.TRES]
    assert h.senas_seen(4)[0].seat == 0
    assert all(h.senas_seen(rival) == [] for rival in (1, 3, 5))

    h = redonda(0, 1)
    h.apply(Action.signal(Sena.TRES))
    assert h.senas_seen(2) == [] and h.senas_seen(4) == []
    assert all(len(h.senas_seen(rival)) == 1 for rival in (1, 3, 5))


def test_notice_rate_follows_the_configured_probability():
    noticed = 0
    for seed in range(500):
        h = redonda(0.8, 0.15, seed)
        h.apply(Action.signal(Sena.DOS))
        noticed += len(h.senas_seen(2))
    assert 0.74 < noticed / 500 < 0.86


def test_sena_records_the_ronda():
    h = redonda(1, 0)
    for _ in range(6):
        h.apply(Action.play(h.hands[h.to_act][0]))
    assert h.to_act == 0  # the 1 de espadas won the first ronda
    h.apply(Action.signal(Sena.TRES))
    assert h.senas_seen(2)[0].ronda == 1


def test_in_a_duelo_only_the_rival_can_see_it():
    duel = Contest(
        [0, 3],
        {0: HANDS[0], 3: HANDS[3]},
        pica_pica=True,
        config=GameConfig(sena_notice_p=1, sena_leak_q=1),
    )
    duel.apply(Action.signal(Sena.BUEN_ENVIDO))
    assert len(duel.senas_seen(3)) == 1
    assert duel.senas_seen(2) == []  # not in this duelo


def test_only_the_official_senas_are_offered():
    # C.2/C.3: no seña for figures (08–10) nor for having no truco cards (11).
    h = redonda(1, 0)
    offered = {a.sena for a in h.legal_actions() if a.kind == K.SENA}
    assert offered == set(Sena)
    assert {s.value for s in offered} == {f"sena_{n:02}" for n in (1, 2, 3, 4, 5, 6, 7, 12)}
