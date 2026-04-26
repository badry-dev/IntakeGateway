
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task import Task
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.db.schemas.task import TaskRunOut, TaskLogOut, TaskRunLogOut, ReplayRequest
from app.workers.tasks import enqueue_replay

router = APIRouter()

def get_retry_info(db: Session, task_id: int, run_id: int) -> tuple[bool, int | None]:
    """Return (is_retry, retry_of_run_id) based on immediate previous run status."""
    previous_run = (
        db.query(TaskRun)
        .filter(TaskRun.task_id == task_id, TaskRun.id < run_id)
        .order_by(TaskRun.id.desc())
        .first()
    )
    if previous_run and previous_run.status == TaskStatus.FAILED.value:
        return True, previous_run.id
    return False, None

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{run_id}", response_model=dict)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific run"""
    task_run = db.query(TaskRun).filter(TaskRun.id == run_id).first()
    if not task_run:
        raise HTTPException(status_code=404, detail="Run not found")

    task = db.query(Task).filter(Task.id == task_run.task_id).first()
    is_retry, retry_of_run_id = get_retry_info(db, task_run.task_id, task_run.id)
    
    # Get execution logs
    execution_logs = db.query(TaskLog).filter(
        TaskLog.task_run_id == run_id
    ).order_by(TaskLog.created_at.asc()).all()
    
    # Get row errors
    row_errors = db.query(TaskRunLog).filter(
        TaskRunLog.task_run_id == run_id
    ).order_by(TaskRunLog.row_number.asc()).all()
    
    return {
        "id": task_run.id,
        "task_id": task_run.task_id,
        "task_name": task.name if task else None,
        "is_retry": is_retry,
        "retry_of_run_id": retry_of_run_id,
        "status": task_run.status,
        "rows_fetched": task_run.rows_fetched,
        "rows_inserted": task_run.rows_inserted,
        "error_count": task_run.error_count,
        "warning_count": task_run.warning_count,
        "started_at": task_run.started_at,
        "ended_at": task_run.ended_at,
        "execution_logs": [
            {
                "id": log.id,
                "task_run_id": log.task_run_id,
                "step_name": log.step_name,
                "message": log.message,
                "details": log.details,
                "created_at": log.created_at
            }
            for log in execution_logs
        ],
        "row_errors": [
            {
                "id": error.id,
                "task_run_id": error.task_run_id,
                "row_number": error.row_number,
                "column_name": error.column_name,
                "error_type": error.error_type,
                "error_message": error.error_message,
                "source_value": error.source_value,
                "created_at": error.created_at
            }
            for error in row_errors
        ]
    }

@router.post("/{run_id}/replay", status_code=202)
def replay_run(run_id: int, payload: ReplayRequest, db: Session = Depends(get_db)):
    """
    Re-run a prior run with the same cursor window.

    Tagged is_replay=True; will NOT advance task.cursor_last_value. Refused
    when the task has upsert_enabled=False unless `force=true` is set, since
    a non-upsert replay would re-insert duplicates.
    """
    prior = db.query(TaskRun).filter(TaskRun.id == run_id).first()
    if not prior:
        raise HTTPException(status_code=404, detail="Run not found")

    task = db.query(Task).filter(Task.id == prior.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task for this run no longer exists")

    if not task.upsert_enabled and not payload.force:
        raise HTTPException(
            status_code=400,
            detail=(
                "Task has upsert_enabled=False; replay would re-insert duplicates. "
                "Pass force=true to override."
            ),
        )

    try:
        celery_task = enqueue_replay(
            task_id=task.id,
            cursor_start=prior.cursor_start,
            cursor_end=prior.cursor_end,
            replay_of_run_id=prior.id,
            force=payload.force,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to enqueue replay: {e}")

    return {
        "status": "enqueued",
        "task_id": task.id,
        "replay_of_run_id": prior.id,
        "cursor_start": prior.cursor_start,
        "cursor_end": prior.cursor_end,
        "force": payload.force,
        "celery_task_id": celery_task.id if celery_task else None,
    }


@router.get("", response_model=list[dict])
def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: Session = Depends(get_db)
):
    """List recent runs with optional status filtering"""
    query = db.query(TaskRun)
    
    # Filter by status if specified
    if status:
        query = query.filter(TaskRun.status == status)
    
    # Apply pagination - order by id if started_at is null
    runs = query.order_by(TaskRun.id.desc()).offset(skip).limit(limit).all()
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"list_runs: Found {len(runs)} runs from database")
    
    task_ids = {run.task_id for run in runs}
    tasks = db.query(Task).filter(Task.id.in_(task_ids)).all() if task_ids else []
    task_name_map = {task.id: task.name for task in tasks}

    result = []
    for run in runs:
        is_retry, retry_of_run_id = get_retry_info(db, run.task_id, run.id)
        result.append(
            {
                "id": run.id,
                "task_id": run.task_id,
                "task_name": task_name_map.get(run.task_id),
                "is_retry": is_retry,
                "retry_of_run_id": retry_of_run_id,
                "status": run.status,
                "rows_fetched": run.rows_fetched,
                "rows_inserted": run.rows_inserted,
                "error_count": run.error_count,
                "started_at": run.started_at,
                "ended_at": run.ended_at,
                "duration_seconds": (run.ended_at - run.started_at).total_seconds() if run.ended_at else None
            }
        )
    logger.info(f"list_runs: Returning {len(result)} runs")
    return result
