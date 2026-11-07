import random

import pytest

from app.truco.config import GameConfig, RuleMode
from app.truco.hand import Action, ActionKind, Contest, IllegalAction, PicaPicaHand
from app.truco.match import Match, MatchError, ResultKind
from app.truco.signals import BodySpot, Sena, SenaEvent
from app.truco.table import order_from
from tests.truco.test_hand import HANDS

K = ActionKind
INTERACTIVE = GameConfig(mode=RuleMode.INTERACTIVE)
# Tantos: seat 0 → 4, 1 → 31, 2 → 24, 3 → 31, 4 → 25, 5 → 31.


def redonda(scores=(0, 0)) -> Contest:
    return Contest(order_from(0), HANDS, pica_pica=False, scores=scores, config=INTERACTIVE)


def act(contest, seat: int, kind: ActionKind) -> None:
    contest.apply(Action(kind), seat)


def kinds(contest, seat: int) -> set[ActionKind]:
    return {a.kind for a in contest.actions_for(seat)}


def play_out(contest) -> None:
    while not contest.finished:
        seat = contest.to_act
        contest.apply(Action.play(contest.hands[seat][0]), seat)


def envido_won_by_seat_0_bluffing(apply) -> None:
    """Seat 0 sings envido, seat 1 quiere, seat 0 declares 33 (they have 4); everyone concedes.

    `apply(action, seat)` is `Contest.apply` or `Match.play`.
    """
    apply(Action(K.ENVIDO), 0)
    apply(Action(K.QUIERO), 1)
    apply(Action.declare(33), 0)
    for seat in (1, 3, 5):
        apply(Action(K.SON_BUENAS), seat)


# --- cantos fuera de turno (13.4–13.6) ---------------------------------------------------


def test_out_of_turn_canto_does_not_block_and_lapses_when_a_card_is_played():
    h = redonda()
    act(h, 3, K.ENVIDO)  # seat 0 is in turn
    assert K.PLAY in kinds(h, 0)
    h.apply(Action.play(HANDS[0][0]), 0)
    assert h.pending == [] and h.envido_calls == []
    assert K.ENVIDO in kinds(h, 1)  # the envido can be sung again


def test_out_of_turn_canto_can_be_answered_by_any_rival():
    h = redonda()
    act(h, 3, K.TRUCO)
    assert all(K.QUIERO in kinds(h, s) for s in (0, 2, 4))
    act(h, 4, K.QUIERO)
    assert h.truco_accepted == 1 and h.truco_holder == 0


def test_canto_in_turn_blocks_play_until_answered():
    h = redonda()
    act(h, 0, K.TRUCO)
    assert K.PLAY not in kinds(h, 0)
    assert h.to_act == 1
    act(h, 5, K.QUIERO)  # any rival may answer
    assert K.PLAY in kinds(h, 0)


def test_envido_goes_first_over_pending_truco():
    h = redonda()
    act(h, 3, K.TRUCO)
    act(h, 3, K.ENVIDO)
    assert h.to_act == 0  # nothing blocks: seat 0 is in turn
    act(h, 2, K.QUIERO)  # answers the envido, not the truco
    assert h.declaration is not None
    assert h.truco_level == 1 and h.pending[0].family == "truco"


# --- irregular cantos and pardon (10.3, 12.3–12.5) --------------------------------------


def test_irregular_canto_can_be_objected():
    h = redonda()
    act(h, 0, K.VALE_CUATRO)  # skipping truco and retruco
    assert h.pending[0].irregular
    assert K.OBJETAR in kinds(h, 1)
    act(h, 1, K.OBJETAR)
    assert h.pending == [] and h.truco_level == 0


def test_irregular_canto_answered_is_validated():
    h = redonda()
    act(h, 0, K.VALE_CUATRO)
    act(h, 1, K.QUIERO)
    play_out(h)
    assert h.points == [4, 0]


def test_raising_without_the_right_is_irregular():
    h = redonda()
    act(h, 0, K.TRUCO)
    act(h, 1, K.QUIERO)  # team 1 holds the right to raise
    act(h, 0, K.RETRUCO)
    assert h.pending[0].irregular


def test_pardon_by_agreement_undoes_the_last_canto():
    h = redonda()
    act(h, 0, K.TRUCO)
    act(h, 2, K.PERDON)
    assert K.ACEPTAR_PERDON in kinds(h, 1)
    act(h, 1, K.ACEPTAR_PERDON)
    assert h.pending == [] and h.truco_level == 0


def test_pardon_must_be_immediate():
    h = redonda()
    act(h, 0, K.TRUCO)
    act(h, 1, K.QUIERO)
    assert K.PERDON not in kinds(h, 0)


# --- declarations (11.4–11.6) ---------------------------------------------------------


def test_declarations_in_order_from_mano():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    assert h.to_act == 0
    assert K.SON_BUENAS not in kinds(h, 0)  # the mano must say a number
    h.apply(Action.declare(4), 0)
    h.apply(Action.declare(31), 1)
    h.apply(Action.declare(24), 2)  # lower: the first number said still counts
    assert h.to_act == 4  # seat 3 skipped, team 1 already holds the best
    act(h, 4, K.SON_BUENAS)
    assert h.declaration is None
    assert h.envido.winner_seat == 1
    assert h.points == [0, 2]


def test_declared_tie_goes_to_the_one_closer_to_mano():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    h.apply(Action.declare(31), 0)
    h.apply(Action.declare(31), 1)
    for seat in (3, 5):
        act(h, seat, K.SON_BUENAS)
    assert h.envido.winner_seat == 0


def test_only_valid_numbers_can_be_declared():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    with pytest.raises(IllegalAction):
        h.apply(Action.declare(15), 0)


# --- reclamos, the engine as referee (11.7, 11.8) ---------------------------------------


def test_reclamo_against_a_bluffing_winner_gives_the_rival_everything():
    h = redonda()
    envido_won_by_seat_0_bluffing(h.apply)
    assert h.points == [2, 0]
    act(h, 3, K.RECLAMAR)
    assert h.claims == [(3, True)]
    assert h.points == [0, 2]
    play_out(h)  # seat 0's team wins the rondas, but the points go to team 1
    assert h.points == [0, 3]


def test_reclamo_against_a_truthful_winner_has_no_effect():
    h = redonda()
    act(h, 0, K.ENVIDO)
    act(h, 1, K.QUIERO)
    h.apply(Action.declare(4), 0)
    h.apply(Action.declare(31), 1)
    act(h, 2, K.SON_BUENAS)
    act(h, 4, K.SON_BUENAS)
    act(h, 0, K.RECLAMAR)
    assert h.claims == [(0, False)]
    assert h.points == [0, 2]
    assert K.RECLAMAR not in kinds(h, 2)  # one reclamo per team


def test_winner_who_put_their_cards_in_the_mazo_cannot_prove():
    for leave, upheld in ((K.MAZO, True), (K.TAPAR, False)):
        h = redonda()
        act(h, 0, K.ENVIDO)
        act(h, 1, K.QUIERO)
        h.apply(Action.declare(4), 0)
        h.apply(Action.declare(31), 1)
        act(h, 2, K.SON_BUENAS)
        act(h, 4, K.SON_BUENAS)
        act(h, 1, leave)
        act(h, 0, K.RECLAMAR)
        assert h.claims == [(0, upheld)]


def test_false_losing_number_counts_only_when_exposed():
    for show, upheld in ((True, True), (False, False)):
        h = redonda()
        act(h, 0, K.ENVIDO)
        act(h, 1, K.QUIERO)
        h.apply(Action.declare(30), 0)  # seat 0 has 4
        h.apply(Action.declare(31), 1)
        act(h, 2, K.SON_BUENAS)
        act(h, 4, K.SON_BUENAS)
        if show:
            act(h, 0, K.MOSTRAR)
        act(h, 1, K.RECLAMAR)
        assert h.claims == [(1, upheld)]


# --- pica-pica (15.5, 15.9) -----------------------------------------------------------


def test_future_duelo_player_can_concede_in_advance():
    p = PicaPicaHand(HANDS, mano=0, config=INTERACTIVE)
    assert p.actions_for(2) == [Action(K.MAZO)]
    p.apply(Action(K.MAZO), 2)
    act(p, 0, K.MAZO)  # duelo 1: team 1 +1
    act(p, 1, K.MAZO)  # duelo 2: team 0 +1
    assert p.finished  # duelo 3 was conceded by seat 2
    assert p.points == [1, 2]


def test_duelo_reclamo_open_until_the_next_duelo_starts():
    for start_next, upheld in ((False, True), (True, None)):
        p = PicaPicaHand(HANDS, mano=0, config=INTERACTIVE)
        act(p, 0, K.ENVIDO)
        act(p, 3, K.QUIERO)
        p.apply(Action.declare(33), 0)  # seat 0 has 4
        act(p, 3, K.SON_BUENAS)
        act(p, 0, K.MAZO)
        assert p.duels[0].points == [2, 1]
        if start_next:
            p.apply(Action.play(HANDS[1][0]), 1)
            assert K.RECLAMAR not in kinds(p, 3)
            continue
        act(p, 3, K.RECLAMAR)
        assert p.duels[0].claims == [(3, upheld)]
        assert p.duels[0].points == [0, 3]
        assert p.current.scores == (0, 3)  # the next duelo was dealt with the right score


# --- Match: reclamos between manos, señas and interference ------------------------------


def interactive_match(first_dealer: int = 5) -> Match:
    return Match(first_dealer=first_dealer, rng=random.Random(1), config=INTERACTIVE)


def test_reclamo_after_the_mano_until_the_next_deal():
    m = interactive_match()
    m.deal(HANDS)
    envido_won_by_seat_0_bluffing(m.play)
    m.play(Action(K.NOS_VAMOS), 0)  # team 0 leaves: team 1 +1
    assert m.hand is None and m.score == [2, 1]
    assert m.actions_for(3) == [Action(K.RECLAMAR)]
    m.play(Action(K.RECLAMAR), 3)
    assert m.score == [0, 3]
    m.deal()
    assert K.RECLAMAR not in {a.kind for a in m.actions_for(3)}


def test_reclamo_can_undo_a_partido_won_by_envido():
    m = interactive_match()
    m.score = [28, 0]
    m.deal(HANDS)
    envido_won_by_seat_0_bluffing(m.play)
    assert m.result.kind == ResultKind.DEPORTIVO and m.score == [30, 0]
    m.play(Action(K.RECLAMAR), 1)
    assert m.result is None and m.score == [28, 2]


def pica_pica_match() -> Match:
    m = interactive_match(first_dealer=0)
    m.score = [4, 0]
    m.deal()
    m.play(Action(K.NOS_VAMOS))  # mano's team (1) leaves: 5-0, pica-pica next
    m.deal()  # dealer 1, mano 2: duelos (2, 5), (3, 0), (4, 1)
    return m


def sena(seat: int, target: int | None = None) -> SenaEvent:
    return SenaEvent(seat, Sena.TRES, BodySpot.LABIO_INFERIOR, 0, 400, target)


def test_seña_from_outside_the_duelo_is_interference():
    m = pica_pica_match()
    m.sena(sena(0))
    assert m.warnings == [1, 0]
    m.play(Action(K.MAZO), 5)  # team 1 leaves, but all points go to team 1 anyway
    assert m.hand.duels[0].points == [0, 1]


def test_interference_by_both_annuls_the_duelo():
    m = pica_pica_match()
    m.sena(sena(0))
    m.sena(sena(1))
    assert m.hand.duels[0].annulled and m.hand.duels[0].points == [0, 0]
    assert m.warnings == [1, 1]
    assert m.hand.current.seats == [3, 0]


def test_seña_in_the_duelo_is_recorded():
    m = pica_pica_match()
    m.sena(sena(2))
    assert m.warnings == [0, 0]
    assert m.hand.current.sena_events == [sena(2)]


def test_seña_rules():
    m = interactive_match()
    m.deal(HANDS)
    m.sena(sena(0, target=2))
    with pytest.raises(IllegalAction):
        m.sena(sena(0, target=1))  # aimed at a rival
    with pytest.raises(ValueError):
        SenaEvent(0, Sena.TRES, BodySpot.NARIZ, 0, 400)
    strict = Match(first_dealer=5)
    strict.deal()
    with pytest.raises(MatchError):
        strict.sena(sena(0))


@pytest.mark.parametrize("seed", range(20))
def test_random_interactive_partidos_end(seed):
    rng = random.Random(seed)
    m = Match(rng=rng, config=INTERACTIVE)
    for _ in range(50_000):
        if m.finished:
            break
        if m.hand is None:
            claims = [s for s in range(6) if m.actions_for(s)]
            if claims and rng.random() < 0.3:
                m.play(Action(K.RECLAMAR), rng.choice(claims))
            if not m.finished:
                m.deal()
            continue
        moves = [(s, a) for s in range(6) for a in m.actions_for(s)]
        seat, action = rng.choice(moves)
        m.play(action, seat)
    assert m.finished
    assert max(m.score) == 30
