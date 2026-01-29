
import asyncio
from datetime import datetime, timezone
from loguru import logger

from app.workers.celery_app import celery_app
from app.services.runner import run_import
from app.db.session import SessionLocal
from app.db.models.task_run import TaskRun, TaskStatus
from app.core.logging import set_task_context, clear_task_context


def on_task_failure(self, exc, task_id, args, kwargs, einfo):
    """Callback for task failure - log to database and dead-letter queue"""
    import_task_id = args[0] if args else kwargs.get('task_id')
    
    # Escape curly braces in error message to prevent loguru formatting issues
    error_msg = str(exc).replace("{", "{{").replace("}", "}}")
    logger.error(
        f"Task import failed for task_id={import_task_id}: {error_msg}",
        exc_info=exc
    )
    
    # Update TaskRun status to FAILED if exists
    try:
        db = SessionLocal()
        # Find the most recent running task run for this task
        task_run = db.query(TaskRun).filter(
            TaskRun.task_id == import_task_id,
            TaskRun.status == TaskStatus.RUNNING.value
        ).order_by(TaskRun.started_at.desc()).first()
        
        if task_run:
            task_run.status = TaskStatus.FAILED.value
            task_run.ended_at = datetime.now(timezone.utc)
            db.commit()
            logger.info(f"Updated TaskRun {task_run.id} status to FAILED")
        
        db.close()
    except Exception as e:
        logger.error(f"Failed to update TaskRun on task failure: {str(e)}")


def on_task_success(self, result, task_id, args, kwargs):
    """Callback for task success - log completion"""
    import_task_id = args[0] if args else kwargs.get('task_id')
    logger.info(f"Task import completed successfully for task_id={import_task_id}")


def on_task_retry(self, exc, task_id, args, kwargs, einfo):
    """Callback for task retry - log retry attempt"""
    import_task_id = args[0] if args else kwargs.get('task_id')
    logger.warning(
        f"Task import retry for task_id={import_task_id}: {str(exc)}. "
        f"Retry {self.request.retries}/{self.max_retries}"
    )


@celery_app.task(
    name="app.workers.tasks.run_import_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minute
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,  # 10 minutes
    retry_jitter=True,
    acks_late=True,  # Acknowledge after task completes
    reject_on_worker_lost=True,
    on_failure=on_task_failure,
    on_success=on_task_success,
    on_retry=on_task_retry
)
def run_import_task(self, task_id: int):
    """
    Celery task to execute data import for a given task ID
    
    Args:
        task_id: ID of the task to import
    
    Returns:
        Dictionary with import results
    
    Configuration:
        - max_retries: 3 attempts
        - retry_backoff: Exponential backoff (60s, 120s, 240s)
        - retry_jitter: Random jitter to prevent thundering herd
        - acks_late: Acknowledge only after successful completion
    """
    try:
        # Set logging context
        set_task_context(task_id=task_id)
        
        logger.info(f"Celery task started for task_id={task_id}")
        
        # Run the async import function
        result = asyncio.run(run_import(task_id))
        
        logger.info(f"Celery task completed for task_id={task_id}: {result}")
        return result
    
    except Exception as exc:
        logger.error(f"Error in Celery task for task_id={task_id}: {str(exc)}")
        
        # Retry with exponential backoff if retries remaining
        if self.request.retries < self.max_retries:
            raise self.retry(exc=exc)
        else:
            # Max retries reached, fail permanently
            raise
    
    finally:
        clear_task_context()


# Convenience function for other modules to enqueue tasks
def enqueue_run(task_id: int):
    """
    Enqueue a task import job to Celery
    
    Args:
        task_id: ID of the task to import
    
    Returns:
        AsyncResult object from Celery
    """
    logger.info(f"Enqueueing import task for task_id={task_id}")
    return run_import_task.delay(task_id)
