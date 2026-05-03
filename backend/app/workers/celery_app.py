import os

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "intakegateway",
    broker=settings.celery_broker,
    backend=settings.celery_backend,
    include=["app.workers.tasks"],
)

# Use default queue for simplicity (can add custom queues later if needed)
# celery_app.conf.task_routes = {"app.workers.tasks.run_import_task": {"queue": "imports"}}

if os.name == "nt":
    # Celery's default prefork pool relies on billiard multiprocessing, which is
    # fragile on Windows and commonly fails with WinError 5/6 handle errors.
    # Use a single in-process worker for local Windows development.
    celery_app.conf.worker_pool = "solo"
    celery_app.conf.worker_concurrency = 1
