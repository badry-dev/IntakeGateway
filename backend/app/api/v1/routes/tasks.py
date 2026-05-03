from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from loguru import logger

from app.db.session import SessionLocal
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.db.schemas.task import (
    TaskCreate,
    TaskOut,
    TaskRunOut,
    TaskStatsOut,
    TaskLogOut,
    TaskRunLogOut,
    BackfillRequest,
    BackfillResponse,
)
from app.workers.tasks import enqueue_run, enqueue_backfill
from app.core.encryption import encrypt_value
from app.services.connection_storage import get_connection_storage

router = APIRouter()


def _require_existing_connection(connection_id: str) -> None:
    if not connection_id:
        raise HTTPException(status_code=400, detail="connection_id is required")

    storage = get_connection_storage()
    if not storage.get_connection(connection_id):
        raise HTTPException(
            status_code=400, detail=f"Connection {connection_id} not found"
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Task CRUD Endpoints
# ============================================================================

def _flatten_p0_submodels(task_data: dict, task_name: str) -> dict:
    """
    Lift structured submodels (oauth / rate_limit / cursor) onto flat Task columns
    and encrypt sensitive OAuth fields. Drops the nested keys before ORM construction.
    Mutates and returns the dict for convenience.
    """
    oauth = task_data.pop("oauth", None)
    if isinstance(oauth, dict):
        # Plaintext on the wire becomes encrypted at rest. The same field-by-field
        # approach as api_key/password keeps the encryption surface explicit and
        # auditable rather than hidden behind an ORM TypeDecorator.
        task_data["oauth_grant_type"] = oauth.get("grant_type")
        task_data["oauth_token_url"] = oauth.get("token_url")
        task_data["oauth_client_id"] = oauth.get("client_id")
        task_data["oauth_scope"] = oauth.get("scope")
        task_data["oauth_audience"] = oauth.get("audience")
        # Key presence (not truthiness) drives whether the column is touched.
        # PUT with explicit null/"" must be able to clear stored credentials —
        # truthiness-only checks left revoked secrets in place forever.
        for src, dst in (
            ("client_secret", "oauth_client_secret"),
            ("access_token", "oauth_access_token"),
            ("refresh_token", "oauth_refresh_token"),
        ):
            if src in oauth:
                value = oauth[src]
                task_data[dst] = encrypt_value(value) if value else None
                if value and src == "client_secret":
                    logger.debug(f"Encrypted oauth_client_secret for task '{task_name}'")

    rl = task_data.pop("rate_limit", None)
    if isinstance(rl, dict):
        task_data["rate_limit_max_retries"] = rl.get("max_retries")
        task_data["rate_limit_max_wait_seconds"] = rl.get("max_wait_seconds")
        task_data["rate_limit_rps"] = rl.get("rps")

    cursor = task_data.pop("cursor", None)
    if isinstance(cursor, dict):
        task_data["cursor_field"] = cursor.get("field")
        task_data["cursor_param_name"] = cursor.get("param_name")
        task_data["cursor_initial_value"] = cursor.get("initial_value")

    return task_data


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    # Check if task with same name exists
    exists = db.query(Task).filter(Task.name == payload.name).first()
    if exists:
        raise HTTPException(
            status_code=400, detail="Task with this name already exists"
        )

    _require_existing_connection(payload.connection_id)

    # Prepare task data and encrypt sensitive fields
    task_data = payload.model_dump()

    # Encrypt api_key if provided
    if task_data.get("api_key"):
        task_data["api_key"] = encrypt_value(task_data["api_key"])
        logger.debug(f"Encrypted api_key for task '{payload.name}'")

    # Encrypt password if provided
    if task_data.get("password"):
        task_data["password"] = encrypt_value(task_data["password"])
        logger.debug(f"Encrypted password for task '{payload.name}'")

    _flatten_p0_submodels(task_data, payload.name)

    task = Task(**task_data)
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=list[TaskOut])
def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_active: bool = Query(None),
    db: Session = Depends(get_db),
):
    """List all tasks with pagination and filtering"""
    query = db.query(Task)

    # Filter by active status if specified
    if is_active is not None:
        query = query.filter(Task.is_active == is_active)

    # Apply pagination
    total = query.count()
    tasks = query.order_by(Task.id.desc()).offset(skip).limit(limit).all()

    return tasks


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    """Get a specific task by ID"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskOut)
def update_task(task_id: int, payload: TaskCreate, db: Session = Depends(get_db)):
    """Update an existing task"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Check if new name conflicts with another task
    if payload.name != task.name:
        exists = db.query(Task).filter(Task.name == payload.name).first()
        if exists:
            raise HTTPException(
                status_code=400, detail="Task with this name already exists"
            )

    _require_existing_connection(payload.connection_id)

    # Prepare update data and encrypt sensitive fields
    update_data = payload.model_dump()

    # Encrypt api_key if provided
    if update_data.get("api_key"):
        update_data["api_key"] = encrypt_value(update_data["api_key"])
        logger.debug(f"Encrypted api_key for task '{payload.name}'")

    # Encrypt password if provided
    if update_data.get("password"):
        update_data["password"] = encrypt_value(update_data["password"])
        logger.debug(f"Encrypted password for task '{payload.name}'")

    _flatten_p0_submodels(update_data, payload.name)

    # Update task with all fields from payload
    for key, value in update_data.items():
        setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    """Delete a task and all associated runs"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Delete associated runs and logs (cascading delete via foreign keys)
    db.delete(task)
    db.commit()


# ============================================================================
# Task Run Endpoints
# ============================================================================


@router.post("/{task_id}/run", status_code=202)
def trigger_task_run(task_id: int, db: Session = Depends(get_db)):
    """Trigger a new run for a task (enqueues to Celery)"""
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not task.connection_id:
        raise HTTPException(
            status_code=400,
            detail="Task requires a destination connection before it can run",
        )

    storage = get_connection_storage()
    if not storage.get_connection(task.connection_id):
        raise HTTPException(
            status_code=400,
            detail="The task's selected destination connection no longer exists",
        )

    # Create TaskRun record in PENDING state
    task_run = TaskRun(
        task_id=task_id,
        status=TaskStatus.PENDING.value,
        started_at=datetime.now(timezone.utc),
    )
    db.add(task_run)
    db.commit()
    db.refresh(task_run)

    # Enqueue to Celery worker
    try:
        celery_task = enqueue_run(task_id)
        return {
            "status": "enqueued",
            "run_id": task_run.id,
            "task_id": task_id,
            "celery_task_id": celery_task.id if celery_task else None,
        }
    except Exception as e:
        # If enqueueing fails, update run status to FAILED
        task_run.status = TaskStatus.FAILED.value
        task_run.ended_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Failed to enqueue task: {str(e)}")


@router.post("/{task_id}/backfill", status_code=202, response_model=BackfillResponse)
def trigger_backfill(task_id: int, payload: BackfillRequest, db: Session = Depends(get_db)):
    """
    Enqueue a backfill run for a fixed cursor window.

    The resulting run is tagged is_backfill=True and will NOT advance
    `task.cursor_last_value` even on success — backfills are intentional
    historical loads and must not rewind production state.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.connection_id:
        raise HTTPException(
            status_code=400,
            detail="Task requires a destination connection before it can run",
        )
    storage = get_connection_storage()
    if not storage.get_connection(task.connection_id):
        raise HTTPException(
            status_code=400,
            detail="The task's selected destination connection no longer exists",
        )
    if not task.cursor_param_name:
        raise HTTPException(
            status_code=400,
            detail="Task has no cursor_param_name configured; backfill requires cursor support",
        )

    # Defensive window-size guard for ISO-date cursors (most common case).
    # We only enforce when both endpoints parse — opaque tokens are passed through.
    if payload.cursor_end:
        try:
            from datetime import datetime as _dt, timedelta
            from app.core.config import settings as _settings

            def _parse_iso_cursor(value: str) -> _dt:
                # datetime.fromisoformat() rejects RFC 3339 'Z' suffix on Python <3.11.
                # Normalize 'Z'/'z' to '+00:00' so common Zulu timestamps actually parse
                # (otherwise the window-size check silently skips for the most likely format).
                normalized = value.strip()
                if normalized.endswith(("Z", "z")):
                    normalized = f"{normalized[:-1]}+00:00"
                return _dt.fromisoformat(normalized)

            start_dt = _parse_iso_cursor(payload.cursor_start)
            end_dt = _parse_iso_cursor(payload.cursor_end)

            # Reject mixed-awareness inputs explicitly with a 400 instead of
            # letting the subtraction surface as a 500 TypeError. Both ends
            # must agree on whether they carry an offset.
            if (start_dt.tzinfo is None) != (end_dt.tzinfo is None):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "cursor_start and cursor_end must both be timezone-aware "
                        "or both be naive"
                    ),
                )

            # Compare full timedeltas, not `.days`. `.days` floors partial days
            # so a window of `N + 23h59m` would slip past a max-N-days check.
            delta = end_dt - start_dt
            if delta.total_seconds() < 0:
                raise HTTPException(
                    status_code=400,
                    detail="cursor_end must be greater than or equal to cursor_start",
                )
            max_delta = timedelta(days=_settings.BACKFILL_MAX_WINDOW_DAYS)
            if delta > max_delta:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Backfill window {delta} exceeds "
                        f"BACKFILL_MAX_WINDOW_DAYS={_settings.BACKFILL_MAX_WINDOW_DAYS}"
                    ),
                )
        except ValueError:
            # Non-ISO cursors: skip the window check.
            pass

    try:
        celery_task = enqueue_backfill(
            task_id=task_id,
            cursor_start=payload.cursor_start,
            cursor_end=payload.cursor_end,
        )
    except Exception as e:
        # `from e` preserves the original Celery / broker traceback so
        # operators can diagnose enqueue failures (broker down, AMQP error, etc.)
        # instead of seeing only the wrapped HTTPException.
        raise HTTPException(status_code=500, detail=f"Failed to enqueue backfill: {e}") from e

    return {
        "status": "enqueued",
        "task_id": task_id,
        "is_backfill": True,
        "cursor_start": payload.cursor_start,
        "cursor_end": payload.cursor_end,
        "celery_task_id": celery_task.id if celery_task else None,
    }


@router.get("/{task_id}/runs", response_model=list[dict])
def list_task_runs(
    task_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: str = Query(None),
    db: Session = Depends(get_db),
):
    """List all runs for a task with pagination and filtering"""
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    query = db.query(TaskRun).filter(TaskRun.task_id == task_id)

    # Filter by status if specified
    if status:
        query = query.filter(TaskRun.status == status)

    # Apply pagination
    runs = query.order_by(TaskRun.started_at.desc()).offset(skip).limit(limit).all()

    return [
        {
            "id": run.id,
            "task_id": run.task_id,
            "status": run.status,
            "records_fetched": run.records_fetched,
            "records_inserted": run.records_inserted,
            "records_failed": run.records_failed,
            "started_at": run.started_at,
            "completed_at": run.completed_at,
            "duration_seconds": (run.completed_at - run.started_at).total_seconds()
            if run.completed_at
            else None,
        }
        for run in runs
    ]


@router.get("/{task_id}/runs/{run_id}", response_model=TaskRunOut)
def get_task_run(task_id: int, run_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific task run"""
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get task run
    task_run = (
        db.query(TaskRun)
        .filter(TaskRun.id == run_id, TaskRun.task_id == task_id)
        .first()
    )
    if not task_run:
        raise HTTPException(status_code=404, detail="Run not found")

    previous_run = (
        db.query(TaskRun)
        .filter(TaskRun.task_id == task_id, TaskRun.id < run_id)
        .order_by(TaskRun.id.desc())
        .first()
    )
    is_retry = (
        previous_run is not None and previous_run.status == TaskStatus.FAILED.value
    )
    retry_of_run_id = previous_run.id if is_retry else None

    # Get execution logs
    execution_logs = (
        db.query(TaskLog)
        .filter(TaskLog.run_id == run_id)
        .order_by(TaskLog.created_at.asc())
        .all()
    )

    # Get row errors
    row_errors = (
        db.query(TaskRunLog)
        .filter(TaskRunLog.run_id == run_id)
        .order_by(TaskRunLog.row_index.asc())
        .all()
    )

    return TaskRunOut(
        id=task_run.id,
        task_id=task_run.task_id,
        task_name=task.name,
        is_retry=is_retry,
        retry_of_run_id=retry_of_run_id,
        status=task_run.status,
        records_fetched=task_run.records_fetched,
        records_inserted=task_run.records_inserted,
        records_failed=task_run.records_failed,
        started_at=task_run.started_at,
        completed_at=task_run.completed_at,
        error_message=task_run.error_message,
        execution_logs=[
            TaskLogOut(
                id=log.id,
                task_id=log.task_id,
                run_id=log.run_id,
                step_name=log.step_name,
                status=log.status,
                message=log.message,
                details=log.details,
                created_at=log.created_at,
            )
            for log in execution_logs
        ],
        row_errors=[
            TaskRunLogOut(
                id=error.id,
                task_id=error.task_id,
                run_id=error.run_id,
                row_index=error.row_index,
                row_data=error.row_data,
                errors=error.errors,
                created_at=error.created_at,
            )
            for error in row_errors
        ],
    )


# ============================================================================
# Task Stats Endpoint
# ============================================================================


@router.get("/{task_id}/stats", response_model=TaskStatsOut)
def get_task_stats(task_id: int, db: Session = Depends(get_db)):
    """Get execution statistics for a task"""
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get all runs for this task
    runs = db.query(TaskRun).filter(TaskRun.task_id == task_id).all()

    total_runs = len(runs)
    successful_runs = len([r for r in runs if r.status == TaskStatus.SUCCESS.value])
    failed_runs = len([r for r in runs if r.status == TaskStatus.FAILED.value])

    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    # Calculate totals
    total_records_fetched = sum(r.records_fetched or 0 for r in runs)
    total_records_inserted = sum(r.records_inserted or 0 for r in runs)
    total_records_failed = sum(r.records_failed or 0 for r in runs)

    # Calculate average duration
    completed_runs = [r for r in runs if r.completed_at]
    avg_duration = 0.0
    if completed_runs:
        durations = [
            (r.completed_at - r.started_at).total_seconds() for r in completed_runs
        ]
        avg_duration = sum(durations) / len(durations)

    # Get last run
    last_run = max(runs, key=lambda r: r.started_at) if runs else None

    return TaskStatsOut(
        task_id=task_id,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        total_records_fetched=total_records_fetched,
        total_records_inserted=total_records_inserted,
        total_records_failed=total_records_failed,
        avg_duration_seconds=avg_duration,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status if last_run else None,
    )
