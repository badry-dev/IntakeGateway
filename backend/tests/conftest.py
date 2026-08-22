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


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "real_ssrf_guard: keep real DNS-resolving SSRF validation (opt-out of "
        "the autouse bypass below)",
    )


@pytest.fixture(autouse=True)
def bypass_fetch_time_ssrf_resolution(request, monkeypatch):
    """Skip fetch-time SSRF DNS resolution except where explicitly marked.

    Most HTTP-layer tests mock ``httpx.AsyncClient``, so the url_guard's real
    DNS resolution inside ``fetch_json`` / token requests would either fail
    (offline) or hit sandbox-local addresses. Mark tests with
    ``@pytest.mark.real_ssrf_guard`` to exercise the real guard.

    Binding notes: ``app.services.api_connector`` binds validate_url_async at
    module scope (both names patched here); ``oauth_token_service`` imports at
    call time via the url_guard module (covered by patching
    ``url_guard.validate_url``, which ``validate_url_async`` calls through);
    schema-level validation in ``schemas/task.py`` retains its own reference
    and stays active everywhere.
    """
    if request.node.get_closest_marker("real_ssrf_guard"):
        yield
        return

    import app.core.url_guard as url_guard

    async def _async_passthrough(url, **kwargs):
        return url

    monkeypatch.setattr(url_guard, "validate_url", lambda url, **kwargs: url)
    import app.services.api_connector as api_connector

    monkeypatch.setattr(api_connector, "validate_url", lambda url, **kwargs: url)
    monkeypatch.setattr(api_connector, "validate_url_async", _async_passthrough)
    yield
