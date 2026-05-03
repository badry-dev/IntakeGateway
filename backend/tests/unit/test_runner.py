"""Unit tests for runner service"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.db.models.column_mapping import ColumnMapping
from app.db.models.task import Task
from app.db.models.task_log import TaskLog
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_run_log import TaskRunLog
from app.services.runner import insert_batch, log_row_error, log_step, run_import


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.refresh = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def mock_task():
    """Mock Task object"""
    return Task(
        id=1,
        name="Test Task",
        endpoint_path="https://api.example.com/data",
        http_method="GET",
        dest_table="CUSTOMERS",
        record_path="$.data",
        is_active=True,
        connection_id="test-conn",
    )


@pytest.fixture
def mock_task_run():
    """Mock TaskRun object"""
    return TaskRun(
        id=1,
        task_id=1,
        status=TaskStatus.PENDING,
        started_at=None,
        ended_at=None,
        rows_fetched=0,
        rows_inserted=0,
        error_count=0,
    )


@pytest.fixture
def mock_column_mappings():
    """Mock ColumnMapping objects"""
    return [
        ColumnMapping(task_id=1, source_field="id", dest_column="CUSTOMER_ID", is_active=True),
        ColumnMapping(
            task_id=1,
            source_field="name",
            dest_column="CUSTOMER_NAME",
            transform_rules='["trim", "upper"]',
            is_active=True,
        ),
        ColumnMapping(task_id=1, source_field="email", dest_column="EMAIL", is_active=True),
    ]


class TestLogStep:
    """Tests for log_step function"""

    def test_log_step_creates_task_log(self, mock_db):
        """Test log_step creates TaskLog entry"""
        log_step(
            db=mock_db,
            task_run_id=1,
            step_name="fetch_api",
            message="Fetching data from API",
            details={"url": "https://api.example.com"},
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify TaskLog was created
        added_log = mock_db.add.call_args[0][0]
        assert isinstance(added_log, TaskLog)
        assert added_log.task_run_id == 1
        assert added_log.step_name == "fetch_api"
        assert added_log.message == "Fetching data from API"
        assert added_log.details == {"url": "https://api.example.com"}


class TestLogRowError:
    """Tests for log_row_error function"""

    def test_log_row_error_creates_task_run_log(self, mock_db):
        """Test log_row_error creates TaskRunLog entry"""
        log_row_error(
            db=mock_db,
            task_run_id=1,
            row_number=5,
            column_name="email",
            error_type="format",
            error_message="Invalid email format",
            source_value="invalid-email",
        )

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

        # Verify TaskRunLog was created
        added_log = mock_db.add.call_args[0][0]
        assert isinstance(added_log, TaskRunLog)
        assert added_log.task_run_id == 1
        assert added_log.row_number == 5
        assert added_log.column_name == "email"
        assert added_log.error_type == "format"
        assert added_log.error_message == "Invalid email format"
        assert added_log.source_value == "invalid-email"


class TestInsertBatch:
    """Tests for insert_batch function"""

    @patch("app.services.runner.text")
    def test_insert_batch_success(self, mock_text, mock_db):
        """Test insert_batch successfully inserts rows"""
        rows = [
            {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE"},
            {"CUSTOMER_ID": 2, "CUSTOMER_NAME": "BOB"},
        ]

        result = insert_batch(db=mock_db, table_name="CUSTOMERS", rows=rows)

        assert result == 2
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called()

    @patch("app.services.runner.text")
    def test_insert_batch_empty_rows(self, mock_text, mock_db):
        """Test insert_batch with empty rows"""
        result = insert_batch(db=mock_db, table_name="CUSTOMERS", rows=[])

        assert result == 0
        mock_db.execute.assert_not_called()

    @patch("app.services.runner.text")
    def test_insert_batch_transaction_rollback_on_error(self, mock_text, mock_db):
        """Test insert_batch rolls back on error"""
        rows = [{"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE"}]

        mock_db.execute.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Database error"):
            insert_batch(db=mock_db, table_name="CUSTOMERS", rows=rows)

        mock_db.rollback.assert_called_once()


class TestRunImport:
    """Tests for run_import function"""

    @pytest.mark.asyncio
    @patch("app.services.runner.get_destination_session")
    @patch("app.services.runner.api_connector")
    @patch("app.services.runner.normalizer")
    @patch("app.services.runner.mapper")
    @patch("app.services.runner.validator")
    @patch("app.services.runner.log_step")
    @patch("app.services.runner.log_row_error")
    @patch("app.services.runner.insert_batch")
    async def test_run_import_success(
        self,
        mock_insert_batch,
        mock_log_row_error,
        mock_log_step,
        mock_validator,
        mock_mapper,
        mock_normalizer,
        mock_api_connector,
        mock_get_destination_session,
        mock_db,
        mock_task,
        mock_task_run,
        mock_column_mappings,
    ):
        """Test run_import complete success flow"""
        mock_db.get.return_value = mock_task

        # Mock API response
        api_response = {
            "data": [
                {"id": 1, "name": "  alice  ", "email": "alice@example.com"},
                {"id": 2, "name": "  bob  ", "email": "bob@example.com"},
            ]
        }
        mock_api_connector.fetch_with_auth = AsyncMock(return_value=api_response)

        # Mock normalizer
        mock_normalizer.select_records.return_value = api_response["data"]
        mock_normalizer.flatten.side_effect = lambda x: x

        # Mock mapper
        mock_mapper.map_rows.return_value = [
            {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "alice@example.com"},
            {"CUSTOMER_ID": 2, "CUSTOMER_NAME": "BOB", "EMAIL": "bob@example.com"},
        ]

        # Mock validator
        mock_validator.validate_rows.return_value = (
            [
                {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "alice@example.com"},
                {"CUSTOMER_ID": 2, "CUSTOMER_NAME": "BOB", "EMAIL": "bob@example.com"},
            ],
            [],
        )

        # Mock insert
        mock_insert_batch.return_value = 2

        # Execute
        result = await run_import(task_id=1, db=mock_db)

        # Verify return values
        assert result["status"] == TaskStatus.SUCCESS.value
        assert result["rows_fetched"] == 2
        assert result["rows_inserted"] == 2
        assert result["error_count"] == 0

        # Verify insert was called
        mock_insert_batch.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.runner.get_destination_session")
    @patch("app.services.runner.api_connector")
    @patch("app.services.runner.normalizer")
    @patch("app.services.runner.mapper")
    @patch("app.services.runner.validator")
    @patch("app.services.runner.log_step")
    @patch("app.services.runner.log_row_error")
    @patch("app.services.runner.insert_batch")
    async def test_run_import_partial_success_with_validation_errors(
        self,
        mock_insert_batch,
        mock_log_row_error,
        mock_log_step,
        mock_validator,
        mock_mapper,
        mock_normalizer,
        mock_api_connector,
        mock_get_destination_session,
        mock_db,
        mock_task,
        mock_task_run,
        mock_column_mappings,
    ):
        """Test run_import with some validation errors"""
        mock_db.get.return_value = mock_task

        # Mock API response
        api_response = {
            "data": [
                {"id": 1, "name": "alice", "email": "alice@example.com"},
                {"id": 2, "name": "bob", "email": "invalid-email"},
            ]
        }
        mock_api_connector.fetch_with_auth = AsyncMock(return_value=api_response)

        mock_normalizer.select_records.return_value = api_response["data"]
        mock_normalizer.flatten.side_effect = lambda x: x

        mock_mapper.map_rows.return_value = [
            {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "alice@example.com"},
            {"CUSTOMER_ID": 2, "CUSTOMER_NAME": "BOB", "EMAIL": "invalid-email"},
        ]

        # Mock validator with one invalid row
        from app.services.validator import ValidationError

        mock_validator.validate_rows.return_value = (
            [{"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "alice@example.com"}],
            [
                {
                    "row": {"CUSTOMER_ID": 2, "CUSTOMER_NAME": "BOB", "EMAIL": "invalid-email"},
                    "errors": [
                        ValidationError("EMAIL", "format", "Invalid email format", "invalid-email")
                    ],
                }
            ],
        )

        mock_insert_batch.return_value = 1

        # Execute
        result = await run_import(task_id=1, db=mock_db)

        # Verify PARTIAL_SUCCESS status
        assert result["status"] == TaskStatus.PARTIAL_SUCCESS.value
        assert result["rows_fetched"] == 2
        assert result["rows_inserted"] == 1
        assert result["error_count"] == 1

        # Verify error was logged
        mock_log_row_error.assert_called()

    @pytest.mark.asyncio
    @patch("app.services.runner.api_connector")
    @patch("app.services.runner.log_step")
    async def test_run_import_api_failure(
        self, mock_log_step, mock_api_connector, mock_db, mock_task, mock_task_run
    ):
        """Test run_import handles API failure"""
        mock_db.get.return_value = mock_task

        # Mock API failure
        mock_api_connector.fetch_with_auth = AsyncMock(side_effect=Exception("API Error"))

        # Execute — should raise
        with pytest.raises(Exception, match="API Error"):
            await run_import(task_id=1, db=mock_db)

    @pytest.mark.asyncio
    async def test_run_import_task_not_found(self, mock_db):
        """Test run_import raises error when task not found"""
        mock_db.get.return_value = None

        with pytest.raises(ValueError, match="Task .* not found"):
            await run_import(task_id=999, db=mock_db)

    @pytest.mark.asyncio
    @patch("app.services.runner.get_destination_session")
    @patch("app.services.runner.api_connector")
    @patch("app.services.runner.normalizer")
    @patch("app.services.runner.mapper")
    @patch("app.services.runner.validator")
    @patch("app.services.runner.log_step")
    @patch("app.services.runner.insert_batch")
    async def test_run_import_all_rows_invalid(
        self,
        mock_insert_batch,
        mock_log_step,
        mock_validator,
        mock_mapper,
        mock_normalizer,
        mock_api_connector,
        mock_get_destination_session,
        mock_db,
        mock_task,
        mock_task_run,
        mock_column_mappings,
    ):
        """Test run_import when all rows are invalid"""
        mock_db.get.return_value = mock_task

        api_response = {"data": [{"id": 1, "name": "alice", "email": "invalid"}]}
        mock_api_connector.fetch_with_auth = AsyncMock(return_value=api_response)

        mock_normalizer.select_records.return_value = api_response["data"]
        mock_normalizer.flatten.side_effect = lambda x: x

        mock_mapper.map_rows.return_value = [
            {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "invalid"}
        ]

        # All rows invalid
        from app.services.validator import ValidationError

        mock_validator.validate_rows.return_value = (
            [],
            [
                {
                    "row": {"CUSTOMER_ID": 1, "CUSTOMER_NAME": "ALICE", "EMAIL": "invalid"},
                    "errors": [
                        ValidationError("EMAIL", "format", "Invalid email format", "invalid")
                    ],
                }
            ],
        )

        # Execute
        result = await run_import(task_id=1, db=mock_db)

        # Verify FAILED status
        assert result["status"] == TaskStatus.FAILED.value
        assert result["rows_inserted"] == 0
        assert result["error_count"] == 1

        # Verify insert was NOT called
        mock_insert_batch.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
