from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.db import get_session
from app.models import Run, RunRead

router = APIRouter(prefix="/runs", tags=["runs"])


@router.get("")
def list_runs(
    pipeline_id: int | None = None, limit: int = 50, session: Session = Depends(get_session)
) -> list[RunRead]:
    query = select(Run).order_by(Run.id.desc()).limit(limit)
    if pipeline_id is not None:
        query = query.where(Run.pipeline_id == pipeline_id)
    return session.exec(query).all()


@router.get("/{run_id}")
def get_run(run_id: int, session: Session = Depends(get_session)) -> RunRead:
    run = session.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "Run not found")
    return run
