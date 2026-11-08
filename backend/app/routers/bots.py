from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, func, select

from app.bots.settings import PRESETS, BotPreset
from app.db import get_session
from app.models import BotConfig, BotConfigCreate, BotConfigRead, BotConfigUpdate

router = APIRouter(prefix="/bots", tags=["bots"])


@router.get("/presets")
def list_presets() -> list[BotPreset]:
    return PRESETS


@router.get("")
def list_bots(session: Session = Depends(get_session)) -> list[BotConfigRead]:
    bots = session.exec(select(BotConfig).order_by(BotConfig.name)).all()
    return [BotConfigRead.model_validate(b) for b in bots]


def _check_name(session: Session, name: str, bot_id: int | None = None) -> None:
    taken = session.exec(
        select(BotConfig).where(func.lower(BotConfig.name) == name.lower())
    ).first()
    if (taken and taken.id != bot_id) or any(p.name.lower() == name.lower() for p in PRESETS):
        raise HTTPException(409, f"A bot named {name!r} already exists")


@router.post("", status_code=201)
def create_bot(body: BotConfigCreate, session: Session = Depends(get_session)) -> BotConfigRead:
    _check_name(session, body.name)
    bot = BotConfig(
        name=body.name,
        settings=body.settings.model_dump(mode="json"),
        character=body.character,
    )
    session.add(bot)
    session.commit()
    session.refresh(bot)
    return BotConfigRead.model_validate(bot)


@router.put("/{bot_id}")
def update_bot(
    bot_id: int, body: BotConfigUpdate, session: Session = Depends(get_session)
) -> BotConfigRead:
    """Change a saved bot. Only the fields sent change; `character: null` clears it."""
    bot = session.get(BotConfig, bot_id)
    if bot is None:
        raise HTTPException(404, "Bot not found")
    if body.name is not None:
        _check_name(session, body.name, bot_id)
        bot.name = body.name
    if body.settings is not None:
        bot.settings = body.settings.model_dump(mode="json")
    if "character" in body.model_fields_set:
        bot.character = body.character
    session.add(bot)
    session.commit()
    session.refresh(bot)
    return BotConfigRead.model_validate(bot)


@router.delete("/{bot_id}", status_code=204)
def delete_bot(bot_id: int, session: Session = Depends(get_session)) -> Response:
    bot = session.get(BotConfig, bot_id)
    if bot is None:
        raise HTTPException(404, "Bot not found")
    session.delete(bot)
    session.commit()
    return Response(status_code=204)
