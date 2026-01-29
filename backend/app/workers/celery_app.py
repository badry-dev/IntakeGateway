
from celery import Celery
from app.core.config import settings

celery_app = Celery("importer",
                    broker=settings.celery_broker,
                    backend=settings.celery_backend,
                    include=["app.workers.tasks"])

# Use default queue for simplicity (can add custom queues later if needed)
# celery_app.conf.task_routes = {"app.workers.tasks.run_import_task": {"queue": "imports"}}
