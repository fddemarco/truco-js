from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Path
from sqlmodel import Session

from app.bots.settings import PRESETS, BotSettings
from app.db import get_session
from app.games import registry
from app.games.characters import CHARACTER_NAMES, Character, assign_characters
from app.games.schemas import (
    ActRequest,
    ChainInfo,
    GameCreate,
    GameCreated,
    GameView,
    Joined,
    JoinRequest,
    ScoringInfo,
    ScoringSetup,
    SeatSetup,
    SenaRequest,
    TokenRequest,
)
from app.games.session import Conflict, Forbidden, GameError, GameSession, NotFound, Seat
from app.games.views import to_action
from app.models import BotConfig
from app.truco.config import GameConfig
from app.truco.envido import EnvidoCall
from app.truco.scoring import (
    MAX_CHAIN_POINTS,
    MAX_TARGET,
    MIN_TARGET,
    REGLAMENTO,
    ChainPoints,
    Scoring,
    ScoringError,
    envido_chains,
    truco_chains,
)
from app.truco.truco import TrucoCall

router = APIRouter(prefix="/games", tags=["games"])

# Tokens travel in headers, never in URLs, so access logs and proxies don't record them.
SeatToken = Annotated[str, Header(alias="X-Seat-Token")]
HostToken = Annotated[str, Header(alias="X-Host-Token")]
SEAT = Path(ge=0, le=5)


def _bot(setup: SeatSetup, session: Session) -> tuple[str | None, Character | None, BotSettings]:
    """A saved bot keeps its name and character; a preset plays as its seat's character."""
    if setup.bot_id is not None:
        saved = session.get(BotConfig, setup.bot_id)
        if saved is None:
            raise HTTPException(422, f"Saved bot {setup.bot_id} not found")
        character = Character(saved.character) if saved.character else None
        return saved.name, character, BotSettings.model_validate(saved.settings)
    preset = next((p for p in PRESETS if p.key == (setup.bot_preset or PRESETS[0].key)), None)
    if preset is None:
        raise HTTPException(422, f"Unknown bot preset {setup.bot_preset!r}")
    return None, None, preset.settings


def _run[T](game_id: str, fn: Callable[[GameSession], T], since: int | None = None) -> T:
    """Call into the game (loaded and saved by the registry), mapping its errors to HTTP
    status codes."""
    try:
        return registry.run(game_id, fn, since)
    except NotFound as e:
        raise HTTPException(404, str(e)) from e
    except Forbidden as e:
        raise HTTPException(403, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    except GameError as e:
        raise HTTPException(400, str(e)) from e


def _scoring(setup: ScoringSetup | None) -> Scoring:
    if setup is None:
        return REGLAMENTO
    try:
        return Scoring.build(
            setup.target,
            [(c.chain, ChainPoints(c.quiero, c.no_quiero)) for c in setup.chains],
        )
    except ScoringError as e:
        raise HTTPException(422, str(e)) from e


@router.get("/scoring")
def scoring_info() -> ScoringInfo:
    """The chains a game can give points to, with the reglamento's (the defaults)."""
    chains = []
    for chain in envido_chains():
        calls = [EnvidoCall(c) for c in chain]
        falta = calls[-1] == EnvidoCall.FALTA_ENVIDO
        quiero = (
            None
            if falta
            else REGLAMENTO.envido_points(calls, True, pica_pica=False, scores=(0, 0), winner=0)
        )
        no_quiero = REGLAMENTO.envido_points(calls, False, pica_pica=False, scores=(0, 0), winner=0)
        chains.append(
            ChainInfo(family="envido", chain=list(chain), quiero=quiero, no_quiero=no_quiero)
        )
    for chain in truco_chains():
        calls = [TrucoCall(c) for c in chain]
        chains.append(
            ChainInfo(
                family="truco",
                chain=list(chain),
                quiero=REGLAMENTO.truco_quiero(calls),
                no_quiero=REGLAMENTO.truco_no_quiero(calls, calls[:-1]),
            )
        )
    return ScoringInfo(
        target=REGLAMENTO.target,
        min_target=MIN_TARGET,
        max_target=MAX_TARGET,
        max_points=MAX_CHAIN_POINTS,
        chains=chains,
    )


@router.post("", status_code=201)
def new_game(body: GameCreate, session: Session = Depends(get_session)) -> GameCreated:
    bots = {i: _bot(s, session) for i, s in enumerate(body.seats) if s.kind == "bot"}
    wanted = [s.character or (bots[i][1] if i in bots else None) for i, s in enumerate(body.seats)]
    characters = assign_characters(wanted)
    seats = []
    for i, setup in enumerate(body.seats):
        character = characters[i]
        if i in bots:
            saved_name, _, settings = bots[i]
            name = setup.name.strip() or saved_name or CHARACTER_NAMES[character]
            seats.append(Seat("bot", name, character, settings))
        else:
            name = setup.name.strip() or f"Jugador {i + 1}"
            seats.append(Seat("human", name, character))
    names = (body.team_names[0], body.team_names[1]) if body.team_names else None
    try:
        config = GameConfig(mode=body.mode, scoring=_scoring(body.scoring))
        game = registry.create_game(config, seats, names)
    except GameError as e:
        raise HTTPException(422, str(e)) from e
    return GameCreated(id=game.id, host_token=game.host_token)


@router.post("/{game_id}/join")
def join_game(game_id: str, body: JoinRequest) -> Joined:
    token = _run(game_id, lambda game: game.join(body.seat, body.name, body.character))
    return Joined(seat=body.seat, token=token)


@router.get("/{game_id}")
def game_view(
    game_id: str,
    look: int | None = None,
    since: int | None = None,
    x_seat_token: Annotated[str | None, Header(alias="X-Seat-Token")] = None,
) -> GameView:
    """The table as the seat of `X-Seat-Token` sees it (none: a spectator).
    `look`: the seat the viewer's camera is on; only its señas are visible (14.4).
    `since`: the last step the client has; the view carries the steps after it."""
    return _run(game_id, lambda game: game.view(x_seat_token, look, since), since)


@router.post("/{game_id}/act")
def act(game_id: str, body: ActRequest, token: SeatToken) -> GameView:
    action = to_action(body.action)
    return _run(game_id, lambda game: game.act(token, action, body.look, body.since), body.since)


@router.post("/{game_id}/deal")
def deal(game_id: str, body: TokenRequest, token: SeatToken) -> GameView:
    """The cutter cuts: the next mano is dealt now instead of at `deal_at`."""
    return _run(game_id, lambda game: game.deal(token, body.look, body.since), body.since)


@router.post("/{game_id}/sena")
def sena(game_id: str, body: SenaRequest, token: SeatToken) -> GameView:
    return _run(
        game_id,
        lambda game: game.sena(
            token, body.sena, body.spot, body.duration_ms, body.target, body.look, body.since
        ),
        body.since,
    )


@router.post("/{game_id}/seats/{seat}/reset")
def reset_seat(game_id: str, host_token: HostToken, seat: Annotated[int, SEAT]) -> GameView:
    """The host frees a human seat whose player lost their token; it can be joined again."""
    return _run(game_id, lambda game: game.reset_seat(host_token, seat))
