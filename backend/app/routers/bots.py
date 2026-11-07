from fastapi import APIRouter, Depends, HTTPException, Response
from sqlmodel import Session, func, select

from app.bots.settings import PRESETS, BotPreset
from app.db import get_session
from app.models import BotConfig, BotConfigCreate, BotConfigRead

router = APIRouter(prefix="/bots", tags=["bots"])


@router.get("/presets")
def list_presets() -> list[BotPreset]:
    return PRESETS


@router.get("")
def list_bots(session: Session = Depends(get_session)) -> list[BotConfigRead]:
    bots = session.exec(select(BotConfig).order_by(BotConfig.name)).all()
    return [BotConfigRead.model_validate(b) for b in bots]


@router.post("", status_code=201)
def create_bot(body: BotConfigCreate, session: Session = Depends(get_session)) -> BotConfigRead:
    name = body.name
    taken = session.exec(
        select(BotConfig).where(func.lower(BotConfig.name) == name.lower())
    ).first()
    if taken or any(p.name.lower() == name.lower() for p in PRESETS):
        raise HTTPException(409, f"A bot named {name!r} already exists")
    bot = BotConfig(name=name, settings=body.settings.model_dump(mode="json"))
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
