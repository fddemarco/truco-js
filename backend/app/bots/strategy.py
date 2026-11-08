"""Choose a bot's next action from its own cards and the table only (no cooperation)."""

import random

from app.bots.settings import BotSettings, CardOrder, Policy
from app.truco.cards import Card
from app.truco.envido import tanto
from app.truco.hand import (
    ENVIDO_ACTIONS,
    TRUCO_ACTIONS,
    Action,
    ActionKind,
    Contest,
    Phase,
    PicaPicaHand,
)
from app.truco.table import team_of
from app.truco.truco import next_call

K = ActionKind


def decide(policy: Policy, value: int, threshold: int) -> bool:
    if policy == Policy.ALWAYS:
        return True
    if policy == Policy.NEVER:
        return False
    return value >= threshold


def choose_card(cards: list[Card], table: list[Card], order: CardOrder, rng: random.Random) -> Card:
    by_rank = sorted(cards, key=lambda c: c.rank)
    if order == CardOrder.STRONGEST_FIRST:
        return by_rank[-1]
    if order == CardOrder.WEAKEST_FIRST:
        return by_rank[0]
    if order == CardOrder.RANDOM:
        return rng.choice(cards)
    # Cheapest winner: beat the best card on the table as cheaply as possible.
    if not table:
        return by_rank[-1]
    to_beat = max(c.rank for c in table)
    winners = [c for c in by_rank if c.rank > to_beat]
    return winners[0] if winners else by_rank[0]


def choose_action(
    hand: Contest | PicaPicaHand,
    settings: BotSettings,
    rng: random.Random,
    seat: int | None = None,
) -> Action:
    """The bot's action for `seat` (default `hand.to_act`) in strict or interactive mode.

    In interactive mode bots stay within the rules: they never sing out of turn or
    irregularly, declare their real tanto (or "son buenas" when they can't win), object to
    irregular cantos, accept pardons and don't file reclamos.
    """
    contest = hand.current if isinstance(hand, PicaPicaHand) else hand
    seat = hand.to_act if seat is None else seat
    if seat is None:
        raise ValueError("nobody is to act")
    legal = hand.legal_actions(seat)
    if not legal:
        raise ValueError(f"seat {seat} has nothing to do")
    team = team_of(seat)
    my_tanto = tanto(contest.dealt[seat])
    kinds = {a.kind for a in legal}

    if contest.phase is Phase.DECLARING:
        assert contest.declaration is not None
        if K.SON_BUENAS in kinds and not contest.declaration.beats(seat, my_tanto):
            return Action(K.SON_BUENAS)
        return Action.declare(my_tanto)
    if K.ACEPTAR_PERDON in kinds:
        return Action(K.ACEPTAR_PERDON)
    if K.OBJETAR in kinds:
        return Action(K.OBJETAR)

    # Only regular cantos: the next truco level, and only with the right to raise (12.1).
    regular = set(ENVIDO_ACTIONS)
    level = contest.truco_level
    pending = contest.pending_canto()
    answering_truco = (
        pending is not None and pending.family == "truco" and team_of(pending.chanter) != team
    )
    if answering_truco or level == 0 or contest.truco_holder == team:
        nxt = next_call(level)
        if nxt is not None:
            regular.add(next(k for k, call in TRUCO_ACTIONS.items() if call == nxt))
    singable = {a.kind: a for a in legal if a.kind in regular}
    if pending is not None and team_of(pending.chanter) == team:
        pending = None  # our own canto: nothing to answer
    action = _decide(contest, seat, settings, rng, singable, pending, my_tanto)
    if action in legal:
        return action
    return next((a for a in legal if a.kind == K.PLAY), legal[0])


def _decide(contest, seat, s, rng, singable, pending, my_tanto) -> Action:
    cards = contest.hands[seat]
    best = max((c.rank for c in cards), default=0)

    def envido_call() -> Action | None:
        preferred = next(k for k, call in ENVIDO_ACTIONS.items() if call == s.envido_call)
        return singable.get(preferred) or next(
            (singable[k] for k in ENVIDO_ACTIONS if k in singable), None
        )

    def wants_envido() -> bool:
        return decide(s.envido_sing, my_tanto, s.envido_sing_threshold)

    truco_call = next((singable[k] for k in TRUCO_ACTIONS if k in singable), None)

    if pending is not None and pending.family == "envido":
        raise_call = envido_call()
        if (
            raise_call
            and s.envido_raise_threshold is not None
            and my_tanto >= s.envido_raise_threshold
        ):
            return raise_call
        accept = decide(s.envido_accept, my_tanto, s.envido_accept_threshold)
        return Action(K.QUIERO if accept else K.NO_QUIERO)

    if pending is not None:  # truco
        call = envido_call()
        if call and wants_envido():
            return call  # el envido está primero (11.11)
        if truco_call and s.truco_raise_threshold is not None and best >= s.truco_raise_threshold:
            return truco_call
        accept = decide(s.truco_accept, best, s.truco_accept_threshold)
        return Action(K.QUIERO if accept else K.NO_QUIERO)

    call = envido_call()
    if call and wants_envido():
        return call
    if truco_call:
        if truco_call.kind == K.TRUCO:
            sing = decide(s.truco_sing, best, s.truco_sing_threshold) or (
                s.truco_sing == Policy.THRESHOLD and rng.random() < s.bluff
            )
        else:  # retruco / vale cuatro after our team accepted
            sing = s.truco_raise_threshold is not None and best >= s.truco_raise_threshold
        if sing:
            return truco_call
    table = [card for _, card in contest.rounds[-1]]
    return Action.play(choose_card(cards, table, s.card_order, rng))
