"""Executes a configured pipeline with dlt and records the outcome as a Run."""

import logging
import traceback

import dlt
from sqlmodel import Session

from app.config import get_settings
from app.db import get_engine
from app.etl.registry import get_source
from app.models import Pipeline, Run, RunStatus, utcnow
from app.warehouse import get_connection

log = logging.getLogger(__name__)


def create_run(session: Session, pipeline: Pipeline) -> Run:
    run = Run(pipeline_id=pipeline.id)
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def execute_run(run_id: int) -> None:
    """Run in a background thread: load data into DuckDB and update the Run row."""
    with Session(get_engine()) as session:
        run = session.get(Run, run_id)
        if run is None:
            return
        pipeline = session.get(Pipeline, run.pipeline_id)
        run.status = RunStatus.running
        session.commit()

        try:
            source = get_source(pipeline.source, pipeline.params)
            dlt_pipeline = dlt.pipeline(
                pipeline_name=f"pipeline_{pipeline.id}",
                destination=dlt.destinations.duckdb(get_connection()),
                dataset_name=pipeline.dataset,
                pipelines_dir=str(get_settings().data_dir / "dlt"),
            )
            dlt_pipeline.run(source)
            counts = dlt_pipeline.last_trace.last_normalize_info.row_counts
            run.rows_loaded = sum(n for table, n in counts.items() if not table.startswith("_dlt"))
            run.status = RunStatus.success
        except Exception as exc:
            log.exception("Pipeline %s failed", pipeline.name)
            run.status = RunStatus.failed
            run.error = f"{exc}\n\n{traceback.format_exc()}"
        finally:
            run.finished_at = utcnow()
            session.commit()
