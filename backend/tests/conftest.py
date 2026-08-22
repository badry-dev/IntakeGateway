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


@pytest.fixture(autouse=True)
def bypass_fetch_time_ssrf_resolution(request, monkeypatch):
    """Skip fetch-time SSRF DNS resolution except in the guard's own tests.

    Most HTTP-layer tests mock ``httpx.AsyncClient``, so the url_guard's real
    DNS resolution inside ``fetch_json`` / token requests would either fail
    (offline) or hit sandbox-local addresses. The guard's behavior is covered
    by tests/unit/test_url_guard.py and the schema-level 422 tests.
    """
    if request.module.__name__ == "tests.unit.test_url_guard":
        yield
        return

    import app.core.url_guard as url_guard
    import app.services.api_connector as api_connector

    # url_guard.validate_url is patched so oauth_token_service's in-function
    # import is covered too; schemas/task.py holds its own reference, so
    # config-time validation stays active.
    monkeypatch.setattr(url_guard, "validate_url", lambda url, **kwargs: url)
    monkeypatch.setattr(api_connector, "validate_url", lambda url, **kwargs: url)
    yield
