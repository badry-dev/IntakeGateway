
from app.workers.celery_app import celery_app
from app.services.runner import run_import

@celery_app.task(name="app.workers.tasks.run_import_task")
def run_import_task(task_id: int):
    return run_import(task_id)

# Thin wrapper for other modules to call
def enqueue_run(task_id: int):
    return run_import_task.delay(task_id)
