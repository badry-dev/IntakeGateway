"""
Pytest configuration for backend tests.

Adds the backend directory to Python path to enable imports.
"""

import sys
from pathlib import Path

import pytest

# Add backend directory to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Initialize database tables and purge stale data before any tests run."""
    from app.db.models.task import Task
    from app.db.models.task_run import TaskRun
    from app.db.models.task_schedule import TaskSchedule
    from app.db.session import SessionLocal, init_app_database

    init_app_database()

    db = SessionLocal()
    try:
        # Remove any data left from previous test runs so uniqueness
        # constraints don't trip up the first test.
        db.query(TaskSchedule).delete()
        db.query(TaskRun).delete()
        db.query(Task).delete()
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
