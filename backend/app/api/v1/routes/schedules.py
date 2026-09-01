"""Schedule management API routes"""

from datetime import UTC, datetime

from croniter import croniter
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.db.models.task_schedule import TaskSchedule
from app.db.schemas.schedule import (
    ScheduleCreate,
    ScheduleListOut,
    ScheduleOut,
    ScheduleUpdate,
    ScheduleWithTaskName,
)
from app.db.session import get_db
from app.services.scheduler import get_scheduler

router = APIRouter(prefix="/api/v1", tags=["schedules"])


@router.post("/tasks/{task_id}/schedule", response_model=ScheduleOut, status_code=201)
def create_schedule(task_id: int, payload: ScheduleCreate, db: Session = Depends(get_db)):
    """
    Create a new cron schedule for a task

    Args:
        task_id: ID of the task to schedule
        payload: Schedule configuration (cron expression)

    Returns:
        Created schedule

    Raises:
        404: Task not found
        400: Invalid cron expression
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        logger.warning(f"Attempted to create schedule for non-existent task {task_id}")
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Check if schedule already exists for this task
    existing_schedule = db.query(TaskSchedule).filter(TaskSchedule.task_id == task_id).first()
    if existing_schedule:
        logger.warning(f"Task {task_id} already has a schedule")
        raise HTTPException(
            status_code=400,
            detail=f"Task {task_id} already has an active schedule. Delete it first to create a new one.",
        )

    # Calculate next run date
    cron = croniter(payload.cron_expression, datetime.now(UTC))
    next_run = cron.get_next(datetime)

    # Create schedule
    schedule = TaskSchedule(
        task_id=task_id,
        cron_expression=payload.cron_expression,
        is_active=payload.is_active,
        next_run_date=next_run,
        created_at=datetime.now(UTC),
    )

    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Register with scheduler service
    try:
        scheduler = get_scheduler()
        scheduler.add_schedule(schedule, task)
        logger.info(
            f"Created schedule {schedule.id} for task {task_id} with cron: {payload.cron_expression}"
        )
    except Exception as e:
        # If scheduler registration fails, rollback database changes
        db.delete(schedule)
        db.commit()
        logger.error(f"Failed to register schedule with scheduler: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to register schedule with scheduler: {str(e)}",
        )

    return schedule


@router.get("/tasks/{task_id}/schedule", response_model=ScheduleOut)
def get_schedule(task_id: int, db: Session = Depends(get_db)):
    """
    Get schedule for a specific task

    Args:
        task_id: ID of the task

    Returns:
        Task's schedule

    Raises:
        404: Task or schedule not found
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    # Get schedule
    schedule = db.query(TaskSchedule).filter(TaskSchedule.task_id == task_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for task {task_id}")

    return schedule


@router.put("/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(schedule_id: int, payload: ScheduleUpdate, db: Session = Depends(get_db)):
    """
    Update an existing schedule

    Args:
        schedule_id: ID of the schedule to update
        payload: Updated schedule configuration

    Returns:
        Updated schedule

    Raises:
        404: Schedule not found
        400: Invalid cron expression
    """
    schedule = db.query(TaskSchedule).filter(TaskSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    # Update fields
    if payload.cron_expression is not None:
        schedule.cron_expression = payload.cron_expression
        # Recalculate next run date
        cron = croniter(payload.cron_expression, datetime.now(UTC))
        schedule.next_run_date = cron.get_next(datetime)

    if payload.is_active is not None:
        schedule.is_active = payload.is_active

    schedule.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(schedule)

    # Reload schedules in scheduler service
    try:
        scheduler = get_scheduler()
        scheduler.reload_schedules()
        logger.info(f"Updated schedule {schedule_id}")
    except Exception as e:
        logger.error(f"Failed to reload schedules in scheduler: {e}")
        # Don't fail the request, but log the error

    return schedule


@router.delete("/schedules/{schedule_id}", status_code=204)
def delete_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Delete a schedule

    Args:
        schedule_id: ID of the schedule to delete

    Raises:
        404: Schedule not found
    """
    schedule = db.query(TaskSchedule).filter(TaskSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    task_id = schedule.task_id

    db.delete(schedule)
    db.commit()

    # Remove from scheduler service
    try:
        scheduler = get_scheduler()
        scheduler.remove_schedule(task_id)
        logger.info(f"Deleted schedule {schedule_id} for task {task_id}")
    except Exception as e:
        logger.error(f"Failed to remove schedule from scheduler: {e}")
        # Don't fail the request, but log the error

    return None


@router.get("/schedules/", response_model=ScheduleListOut)
def list_schedules(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    """
    List all schedules with optional filtering

    Args:
        skip: Number of records to skip (pagination)
        limit: Number of records to return
        is_active: Filter by active status (optional)

    Returns:
        List of schedules with pagination info
    """
    query = db.query(TaskSchedule, Task.name).outerjoin(Task, TaskSchedule.task_id == Task.id)

    # Filter by active status if provided
    if is_active is not None:
        query = query.filter(TaskSchedule.is_active == is_active)

    # Get total count
    total_count = query.count()

    # Apply pagination and ordering
    schedules_with_names = (
        query.order_by(desc(TaskSchedule.created_at)).offset(skip).limit(limit).all()
    )

    # Format response
    schedules = []
    for schedule, task_name in schedules_with_names:
        schedule_dict = {
            **ScheduleOut.model_validate(schedule).model_dump(),
            "task_name": task_name,
        }
        schedules.append(ScheduleWithTaskName(**schedule_dict))

    return ScheduleListOut(schedules=schedules, total_count=total_count, skip=skip, limit=limit)


@router.post("/schedules/{schedule_id}/resume", status_code=200)
def resume_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """
    Resume a paused schedule (for when auto-paused due to failures)

    Args:
        schedule_id: ID of the schedule to resume

    Returns:
        Confirmation message

    Raises:
        404: Schedule not found
    """
    schedule = db.query(TaskSchedule).filter(TaskSchedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(status_code=404, detail=f"Schedule {schedule_id} not found")

    # Reset failure tracking and reactivate
    schedule.is_active = True
    schedule.consecutive_failures = 0
    schedule.updated_at = datetime.now(UTC)

    db.commit()

    # Reload schedules
    try:
        scheduler = get_scheduler()
        scheduler.reload_schedules()
        logger.info(f"Resumed schedule {schedule_id}")
    except Exception as e:
        logger.error(f"Failed to reload schedules: {e}")

    return {"message": f"Schedule {schedule_id} resumed successfully"}
