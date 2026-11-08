"""What each viewer sees of a game: the per-seat `GameView`, its steps, and model conversions.

Pure functions of a `GameSession`'s state; the session holds the lock while they run.
"""

from typing import TYPE_CHECKING

from app.games.schemas import (
    ActionModel,
    CardModel,
    EnvidoView,
    GameView,
    PendingView,
    PlayView,
    ResultView,
    SeatView,
    SenaSeenView,
    SenaView,
    StatView,
    StepView,
)
from app.games.stats import facts
from app.truco.cards import Card, Suit
from app.truco.envido import tanto
from app.truco.hand import Action, Contest
from app.truco.table import SEATS, across, number_of, seats_across, team_of

if TYPE_CHECKING:
    from app.games.session import GameSession, Step

MAX_EVENTS = 40
SENA_VISIBLE_MS = 6000
ONLINE_MS = 20_000  # a human seat seen (a view or a move) this recently is online


def to_card(model: CardModel) -> Card:
    return Card(model.number, Suit(model.suit))


def card_model(card: Card) -> CardModel:
    return CardModel(number=card.number, suit=str(card.suit))


def to_action(model: ActionModel) -> Action:
    card = to_card(model.card) if model.card else None
    return Action(model.kind, card=card, number=model.number, sena=model.sena)


def action_model(action: Action) -> ActionModel:
    card = card_model(action.card) if action.card else None
    return ActionModel(kind=action.kind, card=card, number=action.number, sena=action.sena)


def build_view(game: "GameSession", me: int | None, look: int | None, now: int) -> GameView:
    """The table as it is now for seat `me` (None: a spectator)."""
    m = game.match
    hand = m.hand
    contest = game.contest()
    seats = [seat_view(game, i, contest, now) for i in range(SEATS)]
    view = GameView(
        id=game.id,
        mode=game.config.mode,
        version=game.version,
        server_ms=now,
        started=game.started,
        match_phase=m.phase,
        seats=seats,
        team_names=list(game.team_names),
        score=list(m.score),
        target=game.config.scoring.target,
        malas_max=game.config.scoring.malas_max,
        hand_number=len(m.history) + (1 if hand else 0),
        hand_kind=m.hand_kind if game.started else None,
        dealer=m.dealer,
        phase=hand.phase if hand else None,
        to_act=hand.to_act if hand else None,
        can_deal=game.started and hand is None and not m.finished,
        deal_at=game.deal_at,
        cutter=game.cutter if game.deal_at is not None else None,
        result=ResultView(kind=m.result.kind, winner=m.result.winner) if m.result else None,
        events=game.events[-MAX_EVENTS:],
        me=me,
    )
    if contest is not None:
        fill_contest(view, contest, live_senas=hand is not None, now=now)
    if m.result is not None:
        view.stats = [
            StatView(
                key=f.key,
                seat=f.seat,
                value=f.value,
                mano=f.mano,
                cards=[card_model(c) for c in f.cards],
            )
            for f in facts(game.stats_log)
        ]
    if me is not None:
        focus = look if look is not None and look in seats_across(me) else across(me)
        view.senas = [s for s in view.senas if s.seat in (me, focus)]
        view.my_cards = [card_model(c) for c in game.cards_of(me)]
        if game.started:
            view.actions = [action_model(a) for a in m.actions_for(me)]
        if contest is not None and me in contest.seats:
            view.my_tanto = tanto(contest.dealt[me])
            view.senas_seen = [
                SenaSeenView(seat=s.seat, sena=s.sena, ronda=s.ronda)
                for s in contest.senas_seen(me)
            ]
    return view


def steps_for(
    game: "GameSession", me: int | None, since: int | None
) -> tuple[list[StepView], GameView | None]:
    """The steps after `since`. Without it (a viewer arriving at the table), the current
    mano's steps since the viewer's last move, or since the deal, so the moves they missed
    play out from `base`, the table before them."""
    steps = game.steps
    if since is not None:
        return [step_view(s, me) for s in steps if s.index > since], None
    if game.match.hand is None:
        return [], None
    deal = next((i for i in range(len(steps) - 1, -1, -1) if steps[i].deal), None)
    if deal is None:
        return [], None
    start = deal
    for i in range(deal + 1, len(steps)):
        if me is not None and steps[i].seat == me:
            start = i + 1
    if start == 0 or start >= len(steps):
        return [], None
    return [step_view(s, me) for s in steps[start:]], steps[start - 1].views[me]


def step_view(step: "Step", me: int | None) -> StepView:
    return StepView(index=step.index, seat=step.seat, events=step.events, view=step.views[me])


def fill_contest(view: GameView, contest: Contest, live_senas: bool, now: int) -> None:
    view.mano = contest.mano
    view.pie = contest.seats[-1]
    if contest.pica_pica:
        view.duel = list(contest.seats)
    view.rounds = [
        [PlayView(seat=s, card=card_model(c)) for s, c in ronda] for ronda in contest.rounds
    ]
    view.results = list(contest.results)
    view.pending = [
        PendingView(family=p.family, chanter=p.chanter, in_turn=p.in_turn, irregular=p.irregular)
        for p in contest.pending
    ]
    view.envido_calls = [str(c) for c in contest.envido_calls]
    view.truco_level = contest.truco_level
    view.truco_accepted = contest.truco_accepted
    # Each team's pie: its last player in the play order (the duelo's two in pica-pica).
    for team in (0, 1):
        view.pies[team] = next((x for x in reversed(contest.seats) if team_of(x) == team), None)
    if contest.envido:
        e = contest.envido
        view.envido = EnvidoView(
            calls=[str(c) for c in e.calls],
            accepted=e.accepted,
            team=e.team,
            points=e.points,
            winner_seat=e.winner_seat,
            tantos=dict(e.tantos),
        )
    if contest.declaration:
        view.declarations = dict(contest.declaration.declared)
    recent = now - SENA_VISIBLE_MS
    events = contest.sena_events if live_senas else []
    view.senas = [
        SenaView(
            seat=e.seat,
            sena=e.sena,
            spot=e.spot,
            target=e.target,
            start_ms=e.start_ms,
            duration_ms=e.duration_ms,
        )
        for e in events
        if e.start_ms + e.duration_ms >= recent
    ]


def seat_view(game: "GameSession", seat: int, contest: Contest | None, now: int) -> SeatView:
    s = game.seats[seat]
    in_play = contest is not None and seat in contest.seats
    shown = (
        [card_model(c) for c in contest.dealt[seat]]
        if in_play and contest is not None and seat in contest.shown
        else []
    )
    return SeatView(
        seat=seat,
        team=team_of(seat),
        number=number_of(seat),
        name=s.name,
        character=s.character,
        kind=s.kind,
        joined=s.joined,
        online=s.kind == "bot" or (s.joined and now - s.last_seen_ms < ONLINE_MS),
        in_play=in_play,
        active=in_play and contest is not None and seat in contest.active,
        cards_left=len(game.cards_of(seat)),
        shown=shown,
        played=[card_model(c) for c in game.played(seat)],
    )
