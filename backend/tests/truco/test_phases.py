"""The phases of a contest and the legal-move table of each, in both modes.

See `docs/state-machine.md`. PLAYING: the player in turn plays or sings (7, 13.2).
ANSWERING: a canto sung in turn blocks play until answered (10.1, 13.2). DECLARING:
interactive envido declarations from mano (11.4). FINISHED: nobody acts, except interactive
reclamos (11.7, 15.9).
"""

from app.truco.config import GameConfig, RuleMode
from app.truco.hand import Action, ActionKind, Contest, Phase, PicaPicaHand
from app.truco.match import Match
from app.truco.signals import Sena
from app.truco.table import order_from
from tests.truco.test_hand import HANDS

K = ActionKind
INTERACTIVE = GameConfig(mode=RuleMode.INTERACTIVE)
ENVIDOS = {K.ENVIDO, K.REAL_ENVIDO, K.FALTA_ENVIDO}
SENAS = {Action.signal(s) for s in Sena}


def redonda(config: GameConfig | None = None) -> Contest:
    return Contest(order_from(0), HANDS, pica_pica=False, config=config)


def act(contest: Contest, seat: int, kind: ActionKind) -> None:
    contest.apply(Action(kind), seat)


def kinds(contest: Contest, seat: int) -> set[ActionKind]:
    return {a.kind for a in contest.actions_for(seat)}


def play_out(contest: Contest) -> None:
    while not contest.finished:
        seat = contest.to_act
        contest.apply(Action.play(contest.hands[seat][0]), seat)


# --- strict -------------------------------------------------------------------------------


def test_strict_playing_only_the_player_in_turn_acts():
    h = redonda()
    assert h.phase is Phase.PLAYING and h.to_act == 0
    assert kinds(h, 0) == {K.PLAY, *ENVIDOS, K.TRUCO, K.MAZO, K.NOS_VAMOS, K.SENA}
    assert set(h.actions_for(0)) >= SENAS
    assert all(h.actions_for(s) == [] for s in range(1, 6))


def test_strict_answering_a_truco():
    h = redonda()
    act(h, 0, K.TRUCO)
    assert h.phase is Phase.ANSWERING and h.to_act == 1
    # Envido still open before the truco is answered (13.6).
    assert kinds(h, 1) == {
        K.QUIERO,
        K.NO_QUIERO,
        K.RETRUCO,
        *ENVIDOS,
        K.MAZO,
        K.NOS_VAMOS,
        K.SENA,
    }
    assert all(h.actions_for(s) == [] for s in (0, 2, 3, 4, 5))


def test_strict_answering_an_envido():
    h = redonda()
    act(h, 0, K.ENVIDO)
    assert h.phase is Phase.ANSWERING and h.to_act == 1
    assert kinds(h, 1) == {K.QUIERO, K.NO_QUIERO, *ENVIDOS, K.MAZO, K.NOS_VAMOS, K.SENA}


def test_strict_envido_first_then_back_to_the_truco():
    h = redonda()
    act(h, 0, K.TRUCO)
    act(h, 1, K.ENVIDO)
    assert h.phase is Phase.ANSWERING and h.to_act == 2
    act(h, 2, K.QUIERO)  # the envido is resolved; the truco still waits (11.11)
    assert h.phase is Phase.ANSWERING and h.to_act == 1
    assert K.RETRUCO in kinds(h, 1) and not ENVIDOS & kinds(h, 1)
    act(h, 1, K.QUIERO)
    assert h.phase is Phase.PLAYING and h.to_act == 0


def test_strict_envido_querido_is_resolved_without_declaring():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    assert h.phase is Phase.PLAYING and h.envido is not None and h.to_act == 0


def test_strict_finished():
    h = redonda()
    act(h, 0, K.TRUCO)
    act(h, 1, K.NO_QUIERO)
    assert h.phase is Phase.FINISHED and h.finished and h.to_act is None
    assert all(h.actions_for(s) == [] for s in range(6))


def test_strict_team_leaving_finishes():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.NOS_VAMOS)
    # The unanswered envido counts as no querido (8.5), plus the mano.
    assert h.phase is Phase.FINISHED and h.points == [2, 0]


# --- interactive --------------------------------------------------------------------------


def test_interactive_playing_anyone_sings_only_the_player_in_turn_plays():
    h = redonda(INTERACTIVE)
    assert h.phase is Phase.PLAYING
    base = {*ENVIDOS, K.TRUCO, K.VALE_CUATRO, K.RETRUCO, K.MAZO, K.TAPAR, K.NOS_VAMOS, K.MOSTRAR}
    assert kinds(h, 0) == base | {K.PLAY}
    assert kinds(h, 3) == base


def test_interactive_out_of_turn_canto_does_not_leave_playing():
    h = redonda(INTERACTIVE)
    act(h, 3, K.TRUCO)
    assert h.phase is Phase.PLAYING and h.to_act == 0
    assert {K.PLAY, K.QUIERO} <= kinds(h, 0)
    assert K.PERDON in kinds(h, 3) and K.QUIERO not in kinds(h, 3)


def test_interactive_answering_any_rival_answers_nobody_plays():
    h = redonda(INTERACTIVE)
    act(h, 0, K.TRUCO)
    assert h.phase is Phase.ANSWERING and h.to_act == 1
    for s in (1, 3, 5):
        assert {K.QUIERO, K.NO_QUIERO, K.RETRUCO, *ENVIDOS} <= kinds(h, s)
        assert K.PLAY not in kinds(h, s)
    for s in (0, 2, 4):
        assert not {K.QUIERO, K.PLAY, K.TRUCO} & kinds(h, s)
    assert K.PERDON in kinds(h, 0)


def test_interactive_irregular_canto_can_be_objected():
    h = redonda(INTERACTIVE)
    act(h, 0, K.VALE_CUATRO)  # skips truco and retruco (12.3)
    assert h.phase is Phase.ANSWERING
    assert K.OBJETAR in kinds(h, 1)
    act(h, 1, K.OBJETAR)
    assert h.phase is Phase.PLAYING and h.truco_level == 0


def test_interactive_pardon_returns_to_playing():
    h = redonda(INTERACTIVE)
    act(h, 0, K.TRUCO)
    act(h, 0, K.PERDON)
    assert K.ACEPTAR_PERDON in kinds(h, 1)
    act(h, 1, K.ACEPTAR_PERDON)
    assert h.phase is Phase.PLAYING and h.truco_level == 0 and h.to_act == 0


def test_interactive_declaring():
    h = redonda(INTERACTIVE)
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    assert h.phase is Phase.DECLARING and h.to_act == 0
    assert kinds(h, 0) == {K.DECLARAR}
    assert all(h.actions_for(s) == [] for s in range(1, 6))
    h.apply(Action.declare(30), 0)
    assert h.phase is Phase.DECLARING and h.to_act == 1
    assert kinds(h, 1) == {K.DECLARAR, K.SON_BUENAS}
    h.apply(Action.declare(31), 1)
    for s in (2, 4):
        act(h, s, K.SON_BUENAS)
    assert h.phase is Phase.PLAYING and h.to_act == 0
    assert K.PLAY in kinds(h, 0) and K.RECLAMAR in kinds(h, 0)


def test_interactive_finished_only_reclamos():
    h = redonda(INTERACTIVE)
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    h.apply(Action.declare(33), 0)  # seat 0 has 4
    for s in (1, 3, 5):
        act(h, s, K.SON_BUENAS)
    play_out(h)
    assert h.phase is Phase.FINISHED and h.to_act is None
    assert kinds(h, 1) == kinds(h, 0) == {K.RECLAMAR}
    act(h, 1, K.RECLAMAR)
    assert kinds(h, 3) == set()  # one reclamo per team


def test_reaching_30_finishes_at_once():
    h = Contest(order_from(0), HANDS, pica_pica=False, scores=(0, 29))
    act(h, 0, K.TRUCO)
    act(h, 1, K.ENVIDO)
    act(h, 2, K.NO_QUIERO)  # team 1 reaches 30: the pending truco has no effect (11.10)
    assert h.phase is Phase.FINISHED and h.match_point and h.pending == []


# --- above the contest --------------------------------------------------------------------


def test_pica_pica_phase_follows_the_current_duelo():
    p = PicaPicaHand(HANDS, mano=0)
    assert p.phase is Phase.PLAYING and len(p.duels) == 1
    p.apply(Action(K.MAZO))
    assert p.phase is Phase.PLAYING and len(p.duels) == 2
    p.apply(Action(K.TRUCO))
    assert p.phase is Phase.ANSWERING
    p.apply(Action(K.MAZO))
    p.apply(Action(K.MAZO))
    assert p.phase is Phase.FINISHED and len(p.duels) == 3


def test_match_claims_open_until_the_next_deal():
    m = Match(first_dealer=5, config=INTERACTIVE)
    m.deal(HANDS)
    m.play(Action(K.ENVIDO), 0)
    m.play(Action(K.QUIERO), 1)
    m.play(Action.declare(33), 0)
    for s in (1, 3, 5):
        m.play(Action(K.SON_BUENAS), s)
    m.play(Action(K.NOS_VAMOS), 1)
    assert m.hand is None and m.last_hand.claims_open
    m.deal()
    assert not m.last_hand.claims_open
