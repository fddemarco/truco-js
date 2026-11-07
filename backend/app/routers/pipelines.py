from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.etl.registry import SOURCES
from app.etl.runner import create_run, execute_run
from app.models import Pipeline, PipelineCreate, PipelineRead, PipelineUpdate, Run, RunRead

router = APIRouter(prefix="/pipelines", tags=["pipelines"])


def _get_or_404(session: Session, pipeline_id: int) -> Pipeline:
    pipeline = session.get(Pipeline, pipeline_id)
    if pipeline is None:
        raise HTTPException(404, "Pipeline not found")
    return pipeline


def _validate_source(source: str) -> None:
    if source not in SOURCES:
        raise HTTPException(422, f"Unknown source {source!r}. Available: {sorted(SOURCES)}")


def _commit(session: Session) -> None:
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(409, "A pipeline with that name already exists") from None


@router.get("/sources")
def list_sources() -> list[str]:
    return sorted(SOURCES)


@router.get("")
def list_pipelines(session: Session = Depends(get_session)) -> list[PipelineRead]:
    return session.exec(select(Pipeline).order_by(Pipeline.name)).all()


@router.post("", status_code=201)
def create_pipeline(body: PipelineCreate, session: Session = Depends(get_session)) -> PipelineRead:
    _validate_source(body.source)
    pipeline = Pipeline.model_validate(body)
    session.add(pipeline)
    _commit(session)
    session.refresh(pipeline)
    return pipeline


@router.get("/{pipeline_id}")
def get_pipeline(pipeline_id: int, session: Session = Depends(get_session)) -> PipelineRead:
    return _get_or_404(session, pipeline_id)


@router.patch("/{pipeline_id}")
def update_pipeline(
    pipeline_id: int, body: PipelineUpdate, session: Session = Depends(get_session)
) -> PipelineRead:
    pipeline = _get_or_404(session, pipeline_id)
    changes = body.model_dump(exclude_unset=True)
    if "source" in changes:
        _validate_source(changes["source"])
    pipeline.sqlmodel_update(changes)
    _commit(session)
    session.refresh(pipeline)
    return pipeline


@router.delete("/{pipeline_id}", status_code=204)
def delete_pipeline(pipeline_id: int, session: Session = Depends(get_session)) -> None:
    pipeline = _get_or_404(session, pipeline_id)
    for run in session.exec(select(Run).where(Run.pipeline_id == pipeline_id)):
        session.delete(run)
    session.delete(pipeline)
    session.commit()


@router.post("/{pipeline_id}/run", status_code=202)
def run_pipeline(
    pipeline_id: int, background: BackgroundTasks, session: Session = Depends(get_session)
) -> RunRead:
    pipeline = _get_or_404(session, pipeline_id)
    if not pipeline.enabled:
        raise HTTPException(409, "Pipeline is disabled")
    run = create_run(session, pipeline)
    background.add_task(execute_run, run.id)
    return run
