import asyncio
from datetime import UTC, datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from loguru import logger
from sqlalchemy import select

from app.db.models.task import Task
from app.db.models.task_schedule import TaskSchedule
from app.db.session import SessionLocal
from app.workers.tasks import enqueue_run


class TaskScheduler:
    """APScheduler-based cron scheduler for automated task imports"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.db = SessionLocal()
        self.scheduled_jobs = {}  # Map task_id to APScheduler job_id

    def start(self):
        """Start the scheduler and load all active schedules"""
        logger.info("Starting task scheduler...")
        self.load_schedules()
        self.scheduler.start()
        logger.info("Task scheduler started successfully")

    def shutdown(self):
        """Gracefully shut down the scheduler"""
        logger.info("Shutting down task scheduler...")
        self.scheduler.shutdown()
        self.db.close()
        logger.info("Task scheduler stopped")

    def load_schedules(self):
        """Load all active task schedules from database and add to scheduler"""
        try:
            # Query active schedules with active tasks
            stmt = (
                select(TaskSchedule, Task)
                .join(Task, TaskSchedule.task_id == Task.id)
                .where(TaskSchedule.is_active.is_(True))
                .where(Task.is_active.is_(True))
            )

            results = self.db.execute(stmt).all()

            logger.info(f"Loading {len(results)} active task schedules")

            for task_schedule, task in results:
                self.add_schedule(task_schedule, task)

            logger.info(f"Successfully loaded {len(self.scheduled_jobs)} task schedules")

        except Exception as e:
            logger.error(f"Failed to load task schedules: {str(e)}")
            raise

    def add_schedule(self, task_schedule: TaskSchedule, task: Task):
        """Add a single task schedule to the scheduler"""
        try:
            # Validate cron expression
            if not croniter.is_valid(task_schedule.cron_expression):
                logger.error(
                    f"Invalid cron expression for task {task.id}: {task_schedule.cron_expression}"
                )
                return

            # Remove existing job if present
            if task.id in self.scheduled_jobs:
                self.remove_schedule(task.id)

            # Create cron trigger
            trigger = CronTrigger.from_crontab(task_schedule.cron_expression)

            # Add job to scheduler
            job = self.scheduler.add_job(
                func=self._execute_scheduled_task,
                trigger=trigger,
                args=[task.id, task.name],
                id=f"task_{task.id}",
                name=f"Import: {task.name}",
                replace_existing=True,
            )

            self.scheduled_jobs[task.id] = job.id

            # Update next_run_date in database
            next_run = croniter(task_schedule.cron_expression, datetime.now(UTC)).get_next(datetime)
            task_schedule.next_run_date = next_run
            self.db.commit()

            logger.info(
                f"Scheduled task {task.id} '{task.name}' with cron '{task_schedule.cron_expression}'. "
                f"Next run: {next_run}"
            )

        except Exception as e:
            logger.error(f"Failed to add schedule for task {task.id}: {str(e)}")
            self.db.rollback()

    def remove_schedule(self, task_id: int):
        """Remove a task schedule from the scheduler"""
        if task_id in self.scheduled_jobs:
            job_id = self.scheduled_jobs[task_id]
            self.scheduler.remove_job(job_id)
            del self.scheduled_jobs[task_id]
            logger.info(f"Removed schedule for task {task_id}")

    def _execute_scheduled_task(self, task_id: int, task_name: str):
        """Execute a scheduled task by enqueueing to Celery"""
        try:
            logger.info(f"Triggering scheduled import for task {task_id} '{task_name}'")

            # Enqueue task to Celery
            result = enqueue_run.delay(task_id)

            # Update last_run_date and next_run_date
            task_schedule = (
                self.db.query(TaskSchedule).filter(TaskSchedule.task_id == task_id).first()
            )

            if task_schedule:
                task_schedule.last_run_date = datetime.now(UTC)

                # Calculate next run
                next_run = croniter(task_schedule.cron_expression, datetime.now(UTC)).get_next(
                    datetime
                )
                task_schedule.next_run_date = next_run

                self.db.commit()

                logger.info(
                    f"Enqueued task {task_id} to Celery (job_id: {result.id}). Next run: {next_run}"
                )

        except Exception as e:
            logger.error(f"Failed to execute scheduled task {task_id}: {str(e)}")
            self.db.rollback()

    def reload_schedules(self):
        """Reload all schedules from database (useful after schedule updates)"""
        logger.info("Reloading all task schedules...")

        # Remove all existing jobs
        for task_id in list(self.scheduled_jobs.keys()):
            self.remove_schedule(task_id)

        # Reload from database
        self.load_schedules()


# Global scheduler instance
_scheduler_instance: TaskScheduler | None = None


def get_scheduler() -> TaskScheduler:
    """Get or create the global scheduler instance"""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance


async def run_scheduler():
    """Main entry point to run the scheduler as a long-running process"""
    scheduler = get_scheduler()
    scheduler.start()

    try:
        # Keep running until interrupted
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    logger.info("Starting task scheduler service...")
    asyncio.run(run_scheduler())
