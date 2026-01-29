
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.db.schemas.task import TaskRunOut, TaskLogOut, TaskRunLogOut

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/{run_id}", response_model=TaskRunOut)
def get_run(run_id: int, db: Session = Depends(get_db)):
    """Get detailed information about a specific run"""
    task_run = db.query(TaskRun).filter(TaskRun.id == run_id).first()
    if not task_run:
        raise HTTPException(status_code=404, detail="Run not found")
    
    # Get execution logs
    execution_logs = db.query(TaskLog).filter(
        TaskLog.run_id == run_id
    ).order_by(TaskLog.created_at.asc()).all()
    
    # Get row errors
    row_errors = db.query(TaskRunLog).filter(
        TaskRunLog.run_id == run_id
    ).order_by(TaskRunLog.row_index.asc()).all()
    
    return TaskRunOut(
        id=task_run.id,
        task_id=task_run.task_id,
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
                created_at=log.created_at
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
                created_at=error.created_at
            )
            for error in row_errors
        ]
    )

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
            "duration_seconds": (run.completed_at - run.started_at).total_seconds() if run.completed_at else None
        }
        for run in runs
    ]
