import pytest

from app.truco.cards import Card, Suit
from app.truco.envido import said_in_order
from app.truco.hand import Action, ActionKind, Contest, IllegalAction, PicaPicaHand
from app.truco.table import order_from

K = ActionKind


def c(number: int, suit: str) -> Card:
    return Card(number, Suit(suit))


# Seat 0 is mano. Team 0 = seats 0, 2, 4; team 1 = seats 1, 3, 5.
HANDS = {
    0: [c(1, "espada"), c(3, "copa"), c(4, "oro")],  # tanto 4
    1: [c(4, "copa"), c(5, "copa"), c(6, "copa")],  # 31
    2: [c(2, "oro"), c(12, "basto"), c(4, "basto")],  # 24
    3: [c(5, "oro"), c(6, "oro"), c(4, "espada")],  # 31
    4: [c(7, "oro"), c(11, "basto"), c(5, "basto")],  # 25
    5: [c(6, "espada"), c(10, "espada"), c(5, "espada")],  # 31
}


def redonda(scores=(0, 0)) -> Contest:
    return Contest(order_from(0), HANDS, pica_pica=False, scores=scores)


def act(contest, kind: ActionKind) -> None:
    contest.apply(Action(kind))


def play_first(contest) -> None:
    contest.apply(Action.play(contest.hands[contest.to_act][0]))


def play_out(contest) -> None:
    while not contest.finished:
        play_first(contest)


def kinds(contest) -> set[ActionKind]:
    return {a.kind for a in contest.legal_actions()}


def test_plain_mano_is_worth_one_point():
    h = redonda()
    assert h.to_act == 0
    play_out(h)
    assert h.results == [0, 0]
    assert h.winner == 0
    assert h.points == [1, 0]


def test_ronda_winner_starts_the_next():
    h = redonda()
    h.apply(Action.play(c(4, "oro")))  # seat 0
    for _ in range(5):
        play_first(h)
    # 7 de oros (seat 4) won the first ronda.
    assert h.results == [0]
    assert h.to_act == 4


def test_parda_then_mano_starts():
    duel = Contest(
        [0, 3],
        {
            0: [c(3, "oro"), c(4, "copa"), c(1, "espada")],
            3: [c(3, "copa"), c(5, "copa"), c(2, "oro")],
        },
        pica_pica=True,
    )
    play_first(duel)
    play_first(duel)
    assert duel.results == [None]
    assert duel.to_act == 0
    play_first(duel)  # 4 de copas
    play_first(duel)  # 5 de copas
    assert duel.finished and duel.winner == 1


def test_truco_querido_is_worth_two():
    h = redonda()
    act(h, K.TRUCO)
    assert h.to_act == 1  # first rival to the chanter's right answers
    act(h, K.QUIERO)
    assert h.to_act == 0  # the singer still has to play
    play_out(h)
    assert h.points == [2, 0]


def test_truco_no_querido_ends_the_mano():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.NO_QUIERO)
    assert h.finished
    assert h.points == [1, 0]


def test_only_the_team_that_accepted_can_raise():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.QUIERO)  # team 1 accepted
    assert K.RETRUCO not in kinds(h)  # seat 0 (team 0) is in turn
    play_first(h)
    assert h.to_act == 1
    assert K.RETRUCO in kinds(h)


def test_raise_as_answer_accepts_and_scores():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.RETRUCO)  # seat 1 raises
    assert h.to_act == 2  # next player of team 0 after seat 1
    act(h, K.VALE_CUATRO)
    assert h.to_act == 3
    assert K.VALE_CUATRO not in kinds(h) and K.TRUCO not in kinds(h)
    act(h, K.NO_QUIERO)
    assert h.points == [3, 0]


def test_envido_querido_highest_tanto_wins():
    h = redonda()
    act(h, K.ENVIDO)
    act(h, K.QUIERO)
    assert h.envido.winner_seat == 1  # 31, the first of the 31s from mano
    assert h.points == [0, 2]
    assert K.ENVIDO not in kinds(h)


def test_envido_no_querido():
    h = redonda()
    act(h, K.ENVIDO)
    act(h, K.REAL_ENVIDO)
    act(h, K.NO_QUIERO)
    assert h.points == [0, 2]


def test_envido_tie_goes_to_mano():
    hands = {
        0: [c(7, "espada"), c(6, "espada"), c(4, "copa")],
        3: [c(7, "copa"), c(6, "copa"), c(4, "espada")],
    }
    for seats, winner in (([0, 3], 0), ([3, 0], 3)):
        duel = Contest(seats, hands, pica_pica=True)
        act(duel, K.ENVIDO)
        act(duel, K.QUIERO)
        assert duel.envido.winner_seat == winner


def test_envido_closes_after_first_ronda():
    h = redonda()
    for _ in range(5):
        play_first(h)
    assert K.ENVIDO in kinds(h)  # the last player of the first ronda can still sing
    play_first(h)
    assert K.ENVIDO not in kinds(h)


def test_envido_closes_once_truco_is_querido():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.QUIERO)
    assert K.ENVIDO not in kinds(h)


def test_envido_goes_first_over_a_pending_truco():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.ENVIDO)  # seat 1 answers the truco with envido
    assert h.to_act == 2
    act(h, K.QUIERO)
    assert h.points == [0, 2]
    # The truco is still pending for team 1.
    assert h.to_act == 1
    assert K.QUIERO in kinds(h) and K.ENVIDO not in kinds(h)
    act(h, K.QUIERO)
    assert h.truco_accepted == 1


def test_falta_envido_in_malas_ends_the_partido():
    h = redonda(scores=(10, 12))
    act(h, K.FALTA_ENVIDO)
    act(h, K.QUIERO)
    assert h.finished and h.match_point
    assert h.points == [0, 18]
    assert h.legal_actions() == []


def test_falta_envido_in_buenas():
    h = redonda(scores=(20, 3))
    act(h, K.FALTA_ENVIDO)
    act(h, K.QUIERO)
    assert h.points == [0, 10]
    assert not h.finished


def test_nos_vamos_al_mazo_rejects_pending_cantos():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.ENVIDO)
    act(h, K.NOS_VAMOS)  # seat 2 takes team 0 out
    assert h.finished and h.winner == 1
    assert h.points == [0, 1 + 1]  # envido no querido + truco no querido


def test_individual_mazo_teammates_keep_playing():
    h = redonda()
    act(h, K.TRUCO)
    act(h, K.MAZO)  # seat 1 leaves; the truco is still pending for team 1
    assert not h.finished
    assert h.to_act == 3
    act(h, K.QUIERO)
    play_first(h)  # seat 0
    assert h.to_act == 2  # seat 1 is skipped
    play_out(h)
    assert h.points == [2, 0]


def test_in_turn_player_leaving_passes_the_turn():
    h = redonda()
    act(h, K.MAZO)
    assert h.to_act == 1


def test_team_out_by_individual_mazos():
    duel = Contest([0, 3], {0: HANDS[0], 3: HANDS[3]}, pica_pica=True)
    act(duel, K.TRUCO)
    act(duel, K.QUIERO)
    act(duel, K.MAZO)
    assert duel.finished and duel.winner == 1
    assert duel.points == [0, 2]


def test_pica_pica_has_no_collective_mazo():
    duel = Contest([0, 3], {0: HANDS[0], 3: HANDS[3]}, pica_pica=True)
    assert K.NOS_VAMOS not in kinds(duel)
    assert K.MAZO in kinds(duel)


def test_illegal_action_rejected():
    h = redonda()
    with pytest.raises(IllegalAction):
        act(h, K.QUIERO)
    with pytest.raises(IllegalAction):
        h.apply(Action.play(c(4, "copa")))  # not seat 0's card


def test_pica_pica_plays_three_duelos():
    p = PicaPicaHand(HANDS, mano=0)
    assert p.pairs == [(0, 3), (1, 4), (2, 5)]
    while not p.finished:
        p.apply(Action.play(p.current.hands[p.to_act][0]))
    assert len(p.duels) == 3
    assert p.points == [3, 0]


def test_pica_pica_mazo_with_pending_canto_is_rejection():
    p = PicaPicaHand(HANDS, mano=0)
    act(p, K.ENVIDO)
    act(p, K.MAZO)  # seat 3
    assert p.duels[0].points == [2, 0]  # envido no querido + mano
    assert p.to_act == 1  # second duelo started


def test_pica_pica_falta_envido_is_six():
    p = PicaPicaHand(HANDS, mano=0, scores=(20, 0))
    act(p, K.FALTA_ENVIDO)
    act(p, K.QUIERO)
    assert p.current.points == [0, 6]


def test_pica_pica_stops_when_a_team_reaches_30():
    p = PicaPicaHand(HANDS, mano=0, scores=(29, 0))
    act(p, K.MAZO)  # seat 0 leaves the first duelo, team 1 scores 1
    assert not p.finished
    act(p, K.MAZO)  # seat 1 leaves the second duelo, team 0 reaches 30
    assert p.finished and p.match_point
    assert len(p.duels) == 2


# --- what the table hears of an envido, and what it is worth (both modes use the same) ---


def test_said_in_order_only_says_what_beats_the_best_so_far():
    # 11.4/11.5/11.6: mano declares; rivals declare only to beat it, else son buenas (a tie
    # loses to mano); teammates of the best stay silent.
    tantos = {0: 4, 1: 31, 2: 24, 3: 31, 4: 25, 5: 30}
    assert said_in_order(list(range(6)), tantos) == {0: 4, 1: 31, 2: None, 4: None}
    assert said_in_order([0, 1], {0: 27, 1: 27}) == {0: 27, 1: None}


def test_envido_stakes_while_the_canto_waits():
    # Anexo B.2: envido querido = 2, no querido = 1 to the chanter's team.
    h = redonda()
    assert h.envido_stakes() is None
    act(h, K.ENVIDO)  # seat 0, team 0
    assert h.envido_stakes() == ((2, 2), 1, 0)
    act(h, K.ENVIDO)  # seat 1 raises: envido envido
    assert h.envido_stakes() == ((4, 4), 2, 1)
    act(h, K.QUIERO)
    assert h.envido_stakes() is None


def test_falta_envido_stakes_depend_on_who_wins_it():
    # Anexo B.3: both in malas, the falta is worth what the winner lacks.
    h = redonda(scores=(3, 10))
    act(h, K.FALTA_ENVIDO)
    assert h.envido_stakes() == ((27, 20), 1, 0)
