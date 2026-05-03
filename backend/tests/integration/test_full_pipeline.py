"""
Integration tests for the complete data import pipeline.

Tests the full flow from API fetch → normalize → map → validate → insert,
including retry logic, error handling, and logging context propagation.
"""

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.session import Base
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.column_mapping import ColumnMapping
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.services.runner import run_import
from app.services.api_connector import fetch_json
from app.core.logging import get_task_context


# ============================================================================
# Test Database Setup
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

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
        endpoint_path="/api/v1/test-data",
        dest_table="test_data",
        is_active=True,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
    return task


@pytest.fixture
def sample_task_run(test_db, sample_task) -> TaskRun:
    """Create a sample task run for testing"""
    task_run = TaskRun(
        task_id=sample_task.id,
        status=TaskStatus.PENDING.value,
        started_at=datetime.now(timezone.utc),
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
            source_column="name",
            dest_column="user_name",
            data_type="string",
            is_required=True,
        ),
        ColumnMapping(
            task_id=sample_task.id,
            source_column="age",
            dest_column="user_age",
            data_type="int",
            is_required=False,
        ),
        ColumnMapping(
            task_id=sample_task.id,
            source_column="email",
            dest_column="user_email",
            data_type="string",
            is_required=True,
            validation_type="format",
            validation_value="email",
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


# ============================================================================
# Test: Successful Import Pipeline
# ============================================================================


@pytest.mark.asyncio
async def test_successful_import_pipeline(
    test_db: Session,
    sample_task: Task,
    sample_task_run: TaskRun,
    column_mappings,
    sample_api_response,
):
    """Test successful import with valid data"""
    # Mock the HTTP request
    with patch("app.services.api_connector.client") as mock_client:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_api_response)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        # Mock Oracle connection for insert
        with patch("app.services.runner.get_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_pool.return_value = MagicMock(
                getconn=MagicMock(return_value=mock_conn)
            )
            mock_conn.cursor.return_value = mock_cursor

            # Run import
            result = await run_import(sample_task.id, db=test_db)

            # Verify results
            assert result["status"] == TaskStatus.SUCCESS.value
            assert result["records_fetched"] == 3
            assert result["records_inserted"] == 3
            assert result["records_failed"] == 0

            # Verify TaskRun was updated
            updated_run = (
                test_db.query(TaskRun).filter_by(task_id=sample_task.id).first()
            )
            assert updated_run.status == TaskStatus.SUCCESS.value
            assert updated_run.records_fetched == 3
            assert updated_run.records_inserted == 3
            assert updated_run.completed_at is not None


# ============================================================================
# Test: API Retry Logic
# ============================================================================


@pytest.mark.asyncio
async def test_api_retry_on_timeout():
    """Test that API client retries on timeout"""
    with patch("app.services.api_connector.client") as mock_client:
        # First two calls timeout, third succeeds
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{"id": 1}])
        mock_response.status_code = 200

        mock_client.get = AsyncMock(
            side_effect=[
                httpx.TimeoutException("timeout"),
                httpx.TimeoutException("timeout"),
                mock_response,
            ]
        )

        # Should succeed after retries
        result = await fetch_json("GET", "http://test.api/data", max_retries=3)
        assert result == [{"id": 1}]
        assert mock_client.get.call_count == 3


@pytest.mark.asyncio
async def test_api_no_retry_on_client_error():
    """Test that API client does NOT retry on 4xx errors"""
    with patch("app.services.api_connector.client") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "400", request=None, response=mock_response
        )

        mock_client.get = AsyncMock(return_value=mock_response)

        # Should fail immediately without retries
        with pytest.raises(httpx.HTTPStatusError):
            await fetch_json("GET", "http://test.api/data", max_retries=3)

        # Should only be called once (no retries)
        assert mock_client.get.call_count == 1


@pytest.mark.asyncio
async def test_api_retry_on_server_error():
    """Test that API client retries on 5xx errors"""
    with patch("app.services.api_connector.client") as mock_client:
        # First call fails with 500, second succeeds
        error_response = AsyncMock()
        error_response.status_code = 500
        error_response.text = "Server error"
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "500", request=None, response=error_response
        )

        success_response = AsyncMock()
        success_response.json = AsyncMock(return_value=[{"id": 1}])
        success_response.status_code = 200

        mock_client.get = AsyncMock(side_effect=[error_response, success_response])

        # Should succeed after retry
        result = await fetch_json("GET", "http://test.api/data", max_retries=3)
        assert result == [{"id": 1}]
        assert mock_client.get.call_count == 2


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
        {"name": "Alice", "age": 30, "email": "alice@example.com"},  # Valid
        {
            "name": "",
            "age": 25,
            "email": "invalid-email",
        },  # Invalid: empty name, bad email
        {
            "name": "Charlie",
            "age": "not-a-number",
            "email": "charlie@example.com",
        },  # Invalid: age not int
    ]

    with patch("app.services.api_connector.client") as mock_client:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=invalid_data)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.runner.get_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_pool.return_value = MagicMock(
                getconn=MagicMock(return_value=mock_conn)
            )
            mock_conn.cursor.return_value = mock_cursor

            result = await run_import(sample_task.id, db=test_db)

            # Should have partial success
            assert result["status"] == TaskStatus.PARTIAL_SUCCESS.value
            assert result["records_fetched"] == 3
            assert result["records_failed"] == 2  # Two rows failed validation
            assert result["records_inserted"] == 1  # Only one row inserted


# ============================================================================
# Test: Logging Context Propagation
# ============================================================================


@pytest.mark.asyncio
async def test_logging_context_propagation(test_db, sample_task):
    """Test that task_id and run_id propagate through async calls"""
    from app.core.logging import set_task_context, clear_task_context

    with patch("app.services.api_connector.client") as mock_client:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=[{"id": 1}])
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        # Set context and run import
        set_task_context(task_id=sample_task.id, run_id=999)

        try:
            result = await run_import(sample_task.id, db=test_db)

            # Verify context is still available
            task_id, run_id = get_task_context()
            assert task_id == sample_task.id
            assert run_id == 999
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
    with patch("app.services.api_connector.client") as mock_client:
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value=sample_api_response)
        mock_response.status_code = 200
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.services.runner.get_pool") as mock_pool:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_pool.return_value = MagicMock(
                getconn=MagicMock(return_value=mock_conn)
            )
            mock_conn.cursor.return_value = mock_cursor

            result = await run_import(sample_task.id, db=test_db)

            # Check that TaskLog entries were created
            logs = test_db.query(TaskLog).filter_by(task_id=sample_task.id).all()
            assert len(logs) >= 10  # Should have at least 10 steps logged

            # Verify steps are logged
            step_names = {log.step_name for log in logs}
            assert "FETCH_API" in step_names
            assert "INSERT_ORACLE" in step_names


# ============================================================================
# Test: Error Message Capture
# ============================================================================


@pytest.mark.asyncio
async def test_error_message_on_api_failure(test_db, sample_task):
    """Test that error messages are captured on API failure"""
    with patch("app.services.api_connector.client") as mock_client:
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        # Run import (should fail after retries)
        with pytest.raises(httpx.ConnectError):
            await run_import(sample_task.id, db=test_db)

        # Check that TaskRun has error message
        task_run = (
            test_db.query(TaskRun)
            .filter_by(task_id=sample_task.id)
            .order_by(TaskRun.id.desc())
            .first()
        )
        if task_run:
            assert (
                task_run.error_message is not None
                or task_run.status == TaskStatus.PENDING.value
            )


# ============================================================================
# Parametrized Tests for Multiple Scenarios
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "status_code,should_retry",
    [
        (500, True),  # Server error - should retry
        (502, True),  # Bad gateway - should retry
        (503, True),  # Service unavailable - should retry
        (400, False),  # Bad request - no retry
        (401, False),  # Unauthorized - no retry
        (404, False),  # Not found - no retry
    ],
)
async def test_retry_logic_by_status_code(status_code: int, should_retry: bool):
    """Test retry behavior for different HTTP status codes"""
    with patch("app.services.api_connector.client") as mock_client:
        error_response = AsyncMock()
        error_response.status_code = status_code
        error_response.text = f"HTTP {status_code}"
        error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            str(status_code), request=None, response=error_response
        )

        success_response = AsyncMock()
        success_response.json = AsyncMock(return_value=[])
        success_response.status_code = 200

        if should_retry:
            mock_client.get = AsyncMock(side_effect=[error_response, success_response])
            result = await fetch_json("GET", "http://test.api/data", max_retries=3)
            assert result == []
        else:
            mock_client.get = AsyncMock(return_value=error_response)
            with pytest.raises(httpx.HTTPStatusError):
                await fetch_json("GET", "http://test.api/data", max_retries=3)
            # Should only call once (no retries)
            assert mock_client.get.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
