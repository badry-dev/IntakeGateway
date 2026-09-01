"""Shared response-cap definitions for run detail endpoints.

Both /api/v1/tasks/{id}/runs/{run_id} and /api/v1/runs/{run_id} serialize the
same log/error payload; the limits and the capped query block live here so
the two routers cannot drift apart.
"""

from sqlalchemy.orm import Session

from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog

DEFAULT_LOGS_LIMIT = 200
DEFAULT_ROW_ERRORS_LIMIT = 500
LOGS_LIMIT_BOUND = 1000
ROW_ERRORS_LIMIT_BOUND = 5000


def get_capped_run_logs(
    db: Session,
    run_id: int,
    logs_limit: int = DEFAULT_LOGS_LIMIT,
    row_errors_limit: int = DEFAULT_ROW_ERRORS_LIMIT,
) -> tuple[list[TaskLog], list[TaskRunLog], int]:
    """Return (execution_logs, row_errors, row_errors_total) for a run.

    execution_logs is capped at logs_limit; row_errors at row_errors_limit;
    row_errors_total always reports the UNCAPPED count.
    """
    execution_logs = (
        db.query(TaskLog)
        .filter(TaskLog.task_run_id == run_id)
        .order_by(TaskLog.created_at.asc())
        .limit(logs_limit)
        .all()
    )

    row_errors_query = db.query(TaskRunLog).filter(TaskRunLog.task_run_id == run_id)
    row_errors_total = row_errors_query.count()
    row_errors = (
        row_errors_query.order_by(TaskRunLog.row_number.asc()).limit(row_errors_limit).all()
    )

    return execution_logs, row_errors, row_errors_total
