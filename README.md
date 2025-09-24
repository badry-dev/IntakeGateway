
# API→DB Importer (Python / FastAPI)

MVP skeleton for importing JSON from HTTP APIs into existing Oracle tables.
Includes FastAPI app, Celery worker, Redis, and an APScheduler-based scheduler.

## Stack
- FastAPI (HTTP API)
- Celery + Redis (async runs)
- APScheduler (per-task cron scheduling; enqueues Celery tasks)
- SQLAlchemy + python-oracledb (Oracle connectivity)
- httpx, jsonpath-ng (API + mapping)
- Pydantic Settings (config)

## Quickstart

1. Copy `.env.example` to `.env` and fill values.
2. Use Docker Compose (recommended for dev) or run locally.

### Docker Compose
```bash
docker compose up --build
```

- API: http://localhost:8000/docs
- Scheduler & Worker logs in compose output.

### Local (without Docker)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
# In another terminal:
celery -A app.workers.celery_app.celery_app worker --loglevel=INFO --workdir backend
# Optional scheduler:
python backend/app/services/scheduler.py
```

## Database Tables
The app stores task definitions, schedules, runs, and logs in Oracle. DDL is in `backend/app/db/sql/schema.sql`.
Run the DDL with an Oracle account that has privileges to create these objects.

## Pushing to GitHub
```bash
git init
git add .
git commit -m "feat: initial skeleton for API→DB Importer (FastAPI/Celery/Oracle)"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```
