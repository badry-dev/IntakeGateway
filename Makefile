
    .PHONY: dev worker scheduler fmt

    dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --app-dir backend

    worker:
	celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --workdir backend

    scheduler:
	python backend/app/services/scheduler.py

    fmt:
	python -m black backend || true
