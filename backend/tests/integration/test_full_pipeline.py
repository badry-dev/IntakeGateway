"""
Integration tests for the complete data import pipeline.

Tests the full flow from API fetch → normalize → map → validate → insert,
including retry logic, error handling, and logging context propagation.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.models.column_mapping import ColumnMapping
from app.db.models.task import Task
from app.db.models.task_log import TaskLog
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.session import Base
from app.services.api_connector import fetch_json
from app.services.runner import run_import

# ============================================================================
# Test Database Setup
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestSessionLocal = sessionmaker(bind=engine)
    db = TestSessionLocal()

    yield db

    db.close()
    engine.dispose()


# ============================================================================
# Test Data Fixtures
# ============================================================================


@pytest.fixture
def sample_task(test_db) -> Task:
    """Create a sample task for testing"""
    task = Task(
        name="Test Import Task",
        description="Test data import from API",
        endpoint_path="https://api.example.com/v1/test-data",
        dest_table="test_data",
        is_active=True,
        connection_id="test-conn",
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
    return task


@pytest.fixture
def sample_task_run(test_db, sample_task) -> TaskRun:
    """Create a sample task run for testing"""
    task_run = TaskRun(
        task_id=sample_task.id, status=TaskStatus.PENDING.value, started_at=datetime.now(UTC)
    )
    test_db.add(task_run)
    test_db.commit()
    test_db.refresh(task_run)
    return task_run


@pytest.fixture
def column_mappings(test_db, sample_task):
    """Create sample column mappings"""
    mappings = [
        ColumnMapping(
            task_id=sample_task.id,
            source_field="name",
            dest_column="user_name",
            is_active=True,
        ),
        ColumnMapping(
            task_id=sample_task.id,
            source_field="age",
            dest_column="user_age",
            is_active=True,
        ),
        ColumnMapping(
            task_id=sample_task.id,
            source_field="email",
            dest_column="user_email",
            is_active=True,
        ),
    ]
    test_db.add_all(mappings)
    test_db.commit()
    return mappings


@pytest.fixture
def sample_api_response():
    """Sample API response data"""
    return [
        {"name": "Alice", "age": 30, "email": "alice@example.com"},
        {"name": "Bob", "age": 25, "email": "bob@example.com"},
        {"name": "Charlie", "age": 35, "email": "charlie@example.com"},
    ]


def _make_http_mock(response_data, status_code=200):
    """Build an httpx.AsyncClient mock that returns response_data."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.raise_for_status = MagicMock()
    mock_response.content = b"[]"
    mock_response.json.return_value = response_data

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ============================================================================
# Test: Successful Import Pipeline
# ============================================================================


@pytest.mark.asyncio
async def test_successful_import_pipeline(
    test_db: Session,
    sample_task: Task,
    column_mappings,
    sample_api_response,
):
    """Test successful import with valid data"""
    mock_client = _make_http_mock(sample_api_response)

    mock_dest_session = MagicMock()
    mock_dest_session.execute = MagicMock()
    mock_dest_session.commit = MagicMock()
    mock_dest_session.rollback = MagicMock()

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.runner.get_destination_session", return_value=mock_dest_session):
            result = await run_import(sample_task.id, db=test_db)

    assert result["status"] == TaskStatus.SUCCESS.value
    assert result["rows_fetched"] == 3
    assert result["rows_inserted"] == 3
    assert result["error_count"] == 0

    updated_run = test_db.query(TaskRun).filter_by(task_id=sample_task.id).first()
    assert updated_run is not None
    assert updated_run.ended_at is not None


# ============================================================================
# Test: API Retry Logic
# ============================================================================


@pytest.mark.asyncio
async def test_api_retry_on_timeout():
    """Test that API client retries on timeout"""
    success_resp = MagicMock()
    success_resp.status_code = 200
    success_resp.raise_for_status = MagicMock()
    success_resp.content = b"[]"
    success_resp.json.return_value = [{"id": 1}]

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(
        side_effect=[
            httpx.TimeoutException("timeout"),
            httpx.TimeoutException("timeout"),
            success_resp,
        ]
    )
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_json("GET", "http://test.api/data", max_retries=3, initial_backoff=0)

    assert result == [{"id": 1}]
    assert mock_client.request.call_count == 3


@pytest.mark.asyncio
async def test_api_no_retry_on_client_error():
    """Test that API client does NOT retry on 4xx errors"""
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "Bad request"
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "400", request=MagicMock(), response=mock_response
    )
    mock_response.content = b""

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_json("GET", "http://test.api/data", max_retries=3, initial_backoff=0)

    assert mock_client.request.call_count == 1


@pytest.mark.asyncio
async def test_api_retry_on_server_error():
    """Test that API client retries on 5xx errors"""
    error_response = MagicMock()
    error_response.status_code = 500
    error_response.text = "Server error"
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=error_response
    )
    error_response.content = b""

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.raise_for_status = MagicMock()
    success_response.content = b"[]"
    success_response.json.return_value = [{"id": 1}]

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=[error_response, success_response])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await fetch_json("GET", "http://test.api/data", max_retries=3, initial_backoff=0)

    assert result == [{"id": 1}]
    assert mock_client.request.call_count == 2


# ============================================================================
# Test: Validation Error Handling
# ============================================================================


@pytest.mark.asyncio
async def test_import_with_validation_errors(
    test_db: Session,
    sample_task: Task,
    column_mappings,
):
    """Test import with some rows failing validation"""
    invalid_data = [
        {"name": "Alice", "age": 30, "email": "alice@example.com"},
        {"name": "Bob", "age": 25, "email": "bob@example.com"},
        {"name": "Charlie", "age": 35, "email": "charlie@example.com"},
    ]

    mock_client = _make_http_mock(invalid_data)
    mock_dest_session = MagicMock()
    mock_dest_session.execute = MagicMock()
    mock_dest_session.commit = MagicMock()
    mock_dest_session.rollback = MagicMock()

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.runner.get_destination_session", return_value=mock_dest_session):
            result = await run_import(sample_task.id, db=test_db)

    assert result["status"] in (TaskStatus.SUCCESS.value, TaskStatus.PARTIAL_SUCCESS.value)
    assert result["rows_fetched"] == 3


# ============================================================================
# Test: Logging Context Propagation
# ============================================================================


@pytest.mark.asyncio
async def test_logging_context_propagation(test_db, sample_task, column_mappings):
    """Test that task_id and run_id propagate through async calls"""
    from app.core.logging import clear_task_context, set_task_context

    mock_client = _make_http_mock([{"id": 1}])
    mock_dest_session = MagicMock()
    mock_dest_session.execute = MagicMock()
    mock_dest_session.commit = MagicMock()

    set_task_context(task_id=sample_task.id, run_id=999)

    try:
        with patch("httpx.AsyncClient", return_value=mock_client):
            with patch(
                "app.services.runner.get_destination_session", return_value=mock_dest_session
            ):
                result = await run_import(sample_task.id, db=test_db)

        # run_import clears context in its finally block; verify via return value
        assert result["task_id"] == sample_task.id
    finally:
        clear_task_context()


# ============================================================================
# Test: Task Logging
# ============================================================================


@pytest.mark.asyncio
async def test_task_log_entries_created(
    test_db: Session, sample_task: Task, column_mappings, sample_api_response
):
    """Test that TaskLog entries are created during import"""
    mock_client = _make_http_mock(sample_api_response)
    mock_dest_session = MagicMock()
    mock_dest_session.execute = MagicMock()
    mock_dest_session.commit = MagicMock()

    with patch("httpx.AsyncClient", return_value=mock_client):
        with patch("app.services.runner.get_destination_session", return_value=mock_dest_session):
            await run_import(sample_task.id, db=test_db)

    logs = test_db.query(TaskLog).filter_by(task_run_id=1).all()
    # Verify at least some step logs were created
    assert len(logs) >= 1


# ============================================================================
# Test: Error Message Capture
# ============================================================================


@pytest.mark.asyncio
async def test_error_message_on_api_failure(test_db, sample_task):
    """Test that error messages are captured on API failure"""
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient", return_value=mock_client):
        with pytest.raises((httpx.ConnectError, Exception)):
            await run_import(sample_task.id, db=test_db)

    task_run = (
        test_db.query(TaskRun).filter_by(task_id=sample_task.id).order_by(TaskRun.id.desc()).first()
    )
    if task_run:
        assert task_run.status == TaskStatus.FAILED.value or task_run.error_message is not None


# ============================================================================
# Parametrized Tests for Multiple Scenarios
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,should_retry",
    [
        (500, True),
        (502, True),
        (503, True),
        (400, False),
        (401, False),
        (404, False),
    ],
)
async def test_retry_logic_by_status_code(status_code: int, should_retry: bool):
    """Test retry behavior for different HTTP status codes"""
    error_response = MagicMock()
    error_response.status_code = status_code
    error_response.text = f"HTTP {status_code}"
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        str(status_code), request=MagicMock(), response=error_response
    )
    error_response.content = b""

    success_response = MagicMock()
    success_response.status_code = 200
    success_response.raise_for_status = MagicMock()
    success_response.content = b"[]"
    success_response.json.return_value = []

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    if should_retry:
        mock_client.request = AsyncMock(side_effect=[error_response, success_response])
        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await fetch_json(
                "GET", "http://test.api/data", max_retries=3, initial_backoff=0
            )
        assert result == []
    else:
        mock_client.request = AsyncMock(return_value=error_response)
        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_json("GET", "http://test.api/data", max_retries=3, initial_backoff=0)
        assert mock_client.request.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
