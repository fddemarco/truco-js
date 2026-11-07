from collections.abc import Callable

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.bots.settings import PRESETS, BotSettings
from app.db import get_session
from app.games.schemas import (
    ActRequest,
    GameCreate,
    GameCreated,
    GameView,
    Joined,
    JoinRequest,
    SeatSetup,
    SenaRequest,
    TokenRequest,
)
from app.games.session import (
    Conflict,
    Forbidden,
    GameError,
    GameSession,
    Seat,
    create_game,
    get_game,
    to_action,
)
from app.models import BotConfig
from app.truco.config import GameConfig

router = APIRouter(prefix="/games", tags=["games"])


def _bot(setup: SeatSetup, session: Session) -> tuple[str, BotSettings]:
    if setup.bot_id is not None:
        saved = session.get(BotConfig, setup.bot_id)
        if saved is None:
            raise HTTPException(422, f"Saved bot {setup.bot_id} not found")
        return saved.name, BotSettings.model_validate(saved.settings)
    preset = next((p for p in PRESETS if p.key == (setup.bot_preset or PRESETS[0].key)), None)
    if preset is None:
        raise HTTPException(422, f"Unknown bot preset {setup.bot_preset!r}")
    return preset.name, preset.settings


def _game(game_id: str) -> GameSession:
    game = get_game(game_id)
    if game is None:
        raise HTTPException(404, "Game not found")
    return game


def _run[T](fn: Callable[[], T]) -> T:
    """Call into the session, mapping its errors to HTTP status codes."""
    try:
        return fn()
    except Forbidden as e:
        raise HTTPException(403, str(e)) from e
    except Conflict as e:
        raise HTTPException(409, str(e)) from e
    except GameError as e:
        raise HTTPException(400, str(e)) from e


@router.post("", status_code=201)
def new_game(body: GameCreate, session: Session = Depends(get_session)) -> GameCreated:
    seats = []
    for i, setup in enumerate(body.seats):
        if setup.kind == "bot":
            name, settings = _bot(setup, session)
            seats.append(Seat("bot", setup.name.strip() or name, settings))
        else:
            seats.append(Seat("human", setup.name.strip() or f"Jugador {i + 1}"))
    try:
        game = create_game(GameConfig(mode=body.mode), seats)
    except GameError as e:
        raise HTTPException(422, str(e)) from e
    return GameCreated(id=game.id)


@router.post("/{game_id}/join")
def join_game(game_id: str, body: JoinRequest) -> Joined:
    game = _game(game_id)
    token = _run(lambda: game.join(body.seat, body.name))
    return Joined(seat=body.seat, token=token)


@router.get("/{game_id}")
def game_view(game_id: str, token: str | None = None) -> GameView:
    game = _game(game_id)
    return _run(lambda: game.view(token))


@router.post("/{game_id}/act")
def act(game_id: str, body: ActRequest) -> GameView:
    game = _game(game_id)
    _run(lambda: game.act(body.token, to_action(body.action)))
    return game.view(body.token)


@router.post("/{game_id}/deal")
def deal(game_id: str, body: TokenRequest) -> GameView:
    game = _game(game_id)
    _run(lambda: game.deal(body.token))
    return game.view(body.token)


@router.post("/{game_id}/sena")
def sena(game_id: str, body: SenaRequest) -> GameView:
    game = _game(game_id)
    _run(lambda: game.sena(body.token, body.sena, body.spot, body.duration_ms, body.target))
    return game.view(body.token)
