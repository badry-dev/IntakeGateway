
# Simple scheduler stub that could read task schedules from DB and enqueue Celery tasks.
import time
from loguru import logger
from app.workers.tasks import enqueue_run

if __name__ == "__main__":
    logger.info("Scheduler started (stub). Polling every 60s.")
    while True:
        # TODO: read enabled schedules from DB and enqueue based on cron logic
        # enqueue_run.delay(task_id)
        time.sleep(60)
