from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy.orm import Session

from app.api.v1.run_payloads import (
    DEFAULT_LOGS_LIMIT,
    DEFAULT_ROW_ERRORS_LIMIT,
    LOGS_LIMIT_BOUND,
    ROW_ERRORS_LIMIT_BOUND,
    get_capped_run_logs,
)
from app.core.encryption import encrypt_value
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.schemas.task import (
    BackfillRequest,
    BackfillResponse,
    TaskCreate,
    TaskLogOut,
    TaskOut,
    TaskRunLogOut,
    TaskRunOut,
    TaskStatsOut,
    TaskUpdate,
)
from app.db.session import SessionLocal
from app.services.connection_storage import get_connection_storage
from app.workers.tasks import enqueue_backfill, enqueue_run

router = APIRouter()


def _require_existing_connection(connection_id: str) -> None:
    if not connection_id:
        raise HTTPException(status_code=400, detail="connection_id is required")

    storage = get_connection_storage()
    if not storage.get_connection(connection_id):
        raise HTTPException(status_code=400, detail=f"Connection {connection_id} not found")


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
        #
        # Presence-based assignment: with exclude_unset=True a partial update's
        # oauth dict only contains explicitly-set keys — assigning .get() for
        # every column would clear omitted fields (e.g. updating ONLY scope
        # would wipe grant_type/token_url/client_id).
        if "grant_type" in oauth:
            task_data["oauth_grant_type"] = oauth["grant_type"]
        if "token_url" in oauth:
            task_data["oauth_token_url"] = oauth["token_url"]
        if "client_id" in oauth:
            task_data["oauth_client_id"] = oauth["client_id"]
        if "scope" in oauth:
            task_data["oauth_scope"] = oauth["scope"]
        if "audience" in oauth:
            task_data["oauth_audience"] = oauth["audience"]
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
        if "max_retries" in rl:
            task_data["rate_limit_max_retries"] = rl["max_retries"]
        if "max_wait_seconds" in rl:
            task_data["rate_limit_max_wait_seconds"] = rl["max_wait_seconds"]
        if "rps" in rl:
            task_data["rate_limit_rps"] = rl["rps"]

    cursor = task_data.pop("cursor", None)
    if isinstance(cursor, dict):
        if "field" in cursor:
            task_data["cursor_field"] = cursor["field"]
        if "param_name" in cursor:
            task_data["cursor_param_name"] = cursor["param_name"]
        if "initial_value" in cursor:
            task_data["cursor_initial_value"] = cursor["initial_value"]

    return task_data


@router.post("/", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    """Create a new task"""
    # Check if task with same name exists
    exists = db.query(Task).filter(Task.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="Task with this name already exists")

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
def update_task(task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)):
    """Update an existing task (partial update).

    Only explicitly-set fields are applied. Omitted secrets (api_key,
    password, oauth secrets) are preserved; a secret field present but empty
    string is an explicit clear.
    """
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = payload.model_dump(exclude_unset=True)

    # Check if new name conflicts with another task
    if "name" in update_data and update_data["name"] != task.name:
        exists = db.query(Task).filter(Task.name == update_data["name"]).first()
        if exists:
            raise HTTPException(status_code=400, detail="Task with this name already exists")

    if "connection_id" in update_data:
        _require_existing_connection(update_data["connection_id"])

    # Upsert invariant on the EFFECTIVE state (request merged over stored
    # values): {"upsert_enabled": true} alone must not leave a task with no
    # keys, or the runner silently degrades to plain inserts. Only enforced
    # when the request touches the upsert fields, so an unrelated partial
    # update of a legacy row is not blocked.
    if "upsert_enabled" in update_data or "upsert_keys" in update_data:
        effective_upsert = update_data.get("upsert_enabled", task.upsert_enabled)
        effective_keys = update_data.get("upsert_keys", task.upsert_keys)
        if effective_upsert and not effective_keys:
            raise HTTPException(
                status_code=400,
                detail="upsert_enabled requires at least one column in upsert_keys",
            )

    # Encrypt secrets. Empty string = explicit clear; None (explicit null)
    # also clears; omitted = untouched (key not in update_data).
    if "api_key" in update_data:
        if update_data["api_key"]:
            update_data["api_key"] = encrypt_value(update_data["api_key"])
            logger.debug(f"Encrypted api_key for task '{update_data.get('name', task.name)}'")
        else:
            update_data["api_key"] = None

    if "password" in update_data:
        if update_data["password"]:
            update_data["password"] = encrypt_value(update_data["password"])
            logger.debug(f"Encrypted password for task '{update_data.get('name', task.name)}'")
        else:
            update_data["password"] = None

    _flatten_p0_submodels(update_data, update_data.get("name", task.name))

    # Update task with only the fields explicitly provided
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

    # Enqueue to Celery worker (worker will create the TaskRun record)
    try:
        celery_task = enqueue_run(task_id)
        return {
            "status": "enqueued",
            "task_id": task_id,
            "celery_task_id": celery_task.id if celery_task else None,
        }
    except Exception as e:
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
            from datetime import datetime as _dt
            from datetime import timedelta

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
                        "cursor_start and cursor_end must both be timezone-aware or both be naive"
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
            "rows_fetched": run.rows_fetched,
            "rows_inserted": run.rows_inserted,
            "rows_updated": run.rows_updated,
            "rows_skipped": run.rows_skipped,
            "error_count": run.error_count,
            "warning_count": run.warning_count,
            "error_message": run.error_message,
            "started_at": run.started_at,
            "ended_at": run.ended_at,
            "duration_seconds": (run.ended_at - run.started_at).total_seconds()
            if (run.ended_at and run.started_at)
            else None,
        }
        for run in runs
    ]


@router.get("/{task_id}/runs/{run_id}", response_model=TaskRunOut)
def get_task_run(
    task_id: int,
    run_id: int,
    logs_limit: int = Query(DEFAULT_LOGS_LIMIT, ge=1, le=LOGS_LIMIT_BOUND),
    row_errors_limit: int = Query(DEFAULT_ROW_ERRORS_LIMIT, ge=1, le=ROW_ERRORS_LIMIT_BOUND),
    db: Session = Depends(get_db),
):
    """Get detailed information about a specific task run.

    execution_logs and row_errors are capped (logs_limit / row_errors_limit)
    so a pathological run can't serialize unbounded payloads;
    row_errors_total reports the uncapped count.
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Get task run
    task_run = db.query(TaskRun).filter(TaskRun.id == run_id, TaskRun.task_id == task_id).first()
    if not task_run:
        raise HTTPException(status_code=404, detail="Run not found")

    previous_run = (
        db.query(TaskRun)
        .filter(TaskRun.task_id == task_id, TaskRun.id < run_id)
        .order_by(TaskRun.id.desc())
        .first()
    )
    is_retry = previous_run is not None and previous_run.status == TaskStatus.FAILED.value
    retry_of_run_id = previous_run.id if is_retry else None

    execution_logs, row_errors, row_errors_total = get_capped_run_logs(
        db, run_id, logs_limit, row_errors_limit
    )

    return TaskRunOut(
        id=task_run.id,
        task_id=task_run.task_id,
        task_name=task.name,
        is_retry=is_retry,
        retry_of_run_id=retry_of_run_id,
        status=task_run.status,
        rows_fetched=task_run.rows_fetched,
        rows_inserted=task_run.rows_inserted,
        rows_updated=task_run.rows_updated,
        rows_skipped=task_run.rows_skipped,
        error_count=task_run.error_count,
        warning_count=task_run.warning_count,
        started_at=task_run.started_at,
        ended_at=task_run.ended_at,
        error_message=task_run.error_message,
        row_errors_total=row_errors_total,
        execution_logs=[
            TaskLogOut(
                id=log.id,
                task_run_id=log.task_run_id,
                step_name=log.step_name,
                message=log.message,
                details=log.details,
                created_at=log.created_at,
            )
            for log in execution_logs
        ],
        row_errors=[
            TaskRunLogOut(
                id=error.id,
                task_run_id=error.task_run_id,
                row_number=error.row_number,
                column_name=error.column_name,
                error_type=error.error_type,
                error_message=error.error_message,
                source_value=error.source_value,
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
    """Get execution statistics for a task.

    Aggregated entirely in SQL — previously this loaded EVERY run row into
    Python to sum/count, which degrades linearly with run history.
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    from sqlalchemy import case, func

    # Average duration is dialect-aware: julianday() exists only on SQLite.
    # On other backends, fetch the (small) timestamp pairs and average in
    # Python rather than failing with a 500.
    if db.get_bind().dialect.name == "sqlite":
        duration_ms = func.avg(
            (func.julianday(TaskRun.ended_at) - func.julianday(TaskRun.started_at)) * 86400000.0
        )
        avg_duration_expr = func.coalesce(duration_ms, 0.0).label("avg_duration_ms")
    else:
        avg_duration_expr = None

    agg = (
        db.query(
            func.count(TaskRun.id).label("total_runs"),
            func.sum(case((TaskRun.status == TaskStatus.SUCCESS.value, 1), else_=0)).label(
                "successful_runs"
            ),
            func.sum(case((TaskRun.status == TaskStatus.FAILED.value, 1), else_=0)).label(
                "failed_runs"
            ),
            func.coalesce(func.sum(func.coalesce(TaskRun.rows_fetched, 0)), 0).label(
                "total_rows_fetched"
            ),
            func.coalesce(func.sum(func.coalesce(TaskRun.rows_inserted, 0)), 0).label(
                "total_rows_inserted"
            ),
            func.coalesce(func.sum(func.coalesce(TaskRun.rows_updated, 0)), 0).label(
                "total_rows_updated"
            ),
            func.coalesce(func.sum(func.coalesce(TaskRun.rows_skipped, 0)), 0).label(
                "total_rows_skipped"
            ),
            func.coalesce(func.sum(func.coalesce(TaskRun.error_count, 0)), 0).label("total_errors"),
            *([avg_duration_expr] if avg_duration_expr is not None else []),
        )
        .filter(TaskRun.task_id == task_id)
        .one()
    )

    total_runs = int(agg.total_runs or 0)
    successful_runs = int(agg.successful_runs or 0)
    failed_runs = int(agg.failed_runs or 0)
    success_rate = (successful_runs / total_runs * 100) if total_runs > 0 else 0.0

    if avg_duration_expr is not None:
        avg_duration = float(agg.avg_duration_ms or 0.0) / 1000.0
    else:
        pairs = (
            db.query(TaskRun.started_at, TaskRun.ended_at)
            .filter(
                TaskRun.task_id == task_id,
                TaskRun.started_at.isnot(None),
                TaskRun.ended_at.isnot(None),
            )
            .all()
        )
        durations = [(p.ended_at - p.started_at).total_seconds() for p in pairs]
        avg_duration = (sum(durations) / len(durations)) if durations else 0.0

    last_run = (
        db.query(TaskRun.started_at, TaskRun.status)
        .filter(TaskRun.task_id == task_id)
        .order_by(TaskRun.started_at.desc())
        .first()
    )

    return TaskStatsOut(
        task_id=task_id,
        total_runs=total_runs,
        successful_runs=successful_runs,
        failed_runs=failed_runs,
        success_rate=success_rate,
        total_rows_fetched=int(agg.total_rows_fetched),
        total_rows_inserted=int(agg.total_rows_inserted),
        total_rows_updated=int(agg.total_rows_updated),
        total_rows_skipped=int(agg.total_rows_skipped),
        total_errors=int(agg.total_errors),
        avg_duration_seconds=avg_duration,
        last_run_at=last_run.started_at if last_run else None,
        last_run_status=last_run.status if last_run else None,
    )
