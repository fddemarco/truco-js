import random

import pytest

from app.truco.hand import Action, ActionKind, Contest
from app.truco.match import (
    HandKind,
    Match,
    MatchError,
    ResultKind,
)

K = ActionKind


def concede(m: Match) -> None:
    """The mano's team leaves every contest of the current mano right away."""
    while m.hand is not None:
        hand = m.hand
        collective = isinstance(hand, Contest) and not hand.pica_pica
        m.play(Action(K.NOS_VAMOS if collective else K.MAZO))


def test_first_hands_are_redonda_and_points_are_scored():
    m = Match(first_dealer=5, rng=random.Random(1))  # seat 0 is mano
    m.deal()
    assert m.hand_kind == HandKind.REDONDA
    concede(m)
    assert m.score == [0, 1]
    assert m.dealer == 0  # 5.7: the deck moves right


def test_pica_pica_starts_the_mano_after_reaching_5_and_alternates():
    m = Match(first_dealer=0, rng=random.Random(1))  # seat 1 (team 1) is mano
    m.score = [4, 0]
    m.deal()
    concede(m)
    assert m.score == [5, 0]
    assert m.next_hand_kind() == HandKind.PICA_PICA
    m.deal()
    assert m.hand_kind == HandKind.PICA_PICA
    concede(m)
    assert m.next_hand_kind() == HandKind.REDONDA
    m.deal()
    concede(m)
    assert m.next_hand_kind() == HandKind.PICA_PICA


def test_redonda_reaching_25_ends_pica_pica():
    m = Match(first_dealer=5, rng=random.Random(1))  # seat 0 (team 0) is mano
    m.score = [3, 24]
    m.deal()
    concede(m)
    assert m.score == [3, 25]
    assert m.next_hand_kind() == HandKind.REDONDA


def test_duelos_left_are_played_after_reaching_25():
    m = Match(first_dealer=5, rng=random.Random(1))
    m.score = [4, 23]
    m.deal()
    concede(m)  # 4-24, pica-pica comes next
    m.deal()  # dealer 0: duelos (1, 4), (2, 5), (3, 0)
    assert m.hand_kind == HandKind.PICA_PICA
    m.play(Action(K.MAZO))  # seat 1 leaves: team 0 +1
    m.play(Action(K.MAZO))  # seat 2 leaves: team 1 +1, reaching 25
    assert m.hand is not None  # the third duelo is still played
    m.play(Action(K.MAZO))  # seat 3 leaves: team 0 +1
    assert m.score == [6, 25]
    assert m.next_hand_kind() == HandKind.REDONDA


def test_score_is_capped_at_30_and_ends_the_partido():
    m = Match(first_dealer=5, rng=random.Random(1))
    m.score = [0, 29]
    m.deal()
    m.play(Action(K.TRUCO))
    m.play(Action(K.QUIERO))
    m.play(Action(K.NOS_VAMOS))
    assert m.score == [0, 30]
    assert m.result.kind == ResultKind.DEPORTIVO and m.result.winner == 1
    with pytest.raises(MatchError):
        m.deal()


def test_second_disciplinary_warning_loses_the_partido():
    m = Match(first_dealer=0, rng=random.Random(1))
    m.warn(1)
    assert not m.finished
    m.warn(1)
    assert m.result.kind == ResultKind.SANCION and m.result.winner == 0


def test_sanctions_apply_until_homologation():
    m = Match(first_dealer=5, rng=random.Random(1))
    m.score = [0, 29]
    m.deal()
    concede(m)
    assert m.result.winner == 1
    m.warn(1)
    m.warn(1)
    assert m.result.kind == ResultKind.SANCION and m.result.winner == 0
    m.homologate()
    with pytest.raises(MatchError):
        m.warn(0)


def test_disqualification_and_forfeits():
    m = Match(first_dealer=0)
    m.disqualify(0, 1)
    assert m.result.kind == ResultKind.DOBLE_DESCALIFICACION and m.result.winner is None

    m = Match(first_dealer=0)
    m.disqualify(0)
    assert m.result.kind == ResultKind.DESCALIFICACION and m.result.winner == 1

    m = Match(first_dealer=0)
    m.forfeit(1, ResultKind.AUSENCIA)
    assert m.result.winner == 0 and m.result.administrative
    with pytest.raises(ValueError):
        Match(first_dealer=0).forfeit(1, ResultKind.SANCION)


@pytest.mark.parametrize("seed", range(40))
def test_random_partidos_follow_the_rules(seed):
    rng = random.Random(seed)
    m = Match(rng=rng)
    reached_5_at = reached_25_at = None
    while not m.finished:
        m.deal()
        while m.hand is not None:
            m.play(rng.choice(m.hand.legal_actions()))
        i = len(m.history) - 1
        if reached_5_at is None and max(m.score) >= 5:
            reached_5_at = i
        if reached_25_at is None and max(m.score) >= 25:
            reached_25_at = i

    kinds = [h.kind for h in m.history]
    assert m.result.kind == ResultKind.DEPORTIVO
    assert m.score[m.result.winner] == 30 and m.score[1 - m.result.winner] < 30
    assert HandKind.PICA_PICA not in kinds[: (reached_5_at or 0) + 1]
    for a, b in zip(kinds, kinds[1:], strict=False):
        assert not (a == b == HandKind.PICA_PICA)
    if (
        reached_5_at is not None
        and reached_5_at + 1 < len(kinds)
        and (reached_25_at is None or reached_25_at > reached_5_at)
    ):
        assert kinds[reached_5_at + 1] == HandKind.PICA_PICA
    if reached_25_at is not None:
        assert HandKind.PICA_PICA not in kinds[reached_25_at + 1 :]
