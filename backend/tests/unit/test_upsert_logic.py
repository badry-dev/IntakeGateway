"""Unit tests for upsert and skip logic in runner service (Phase 8)"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.exc import IntegrityError, DatabaseError

from app.services.runner import (
    RowStatus,
    RowResult,
    _should_skip,
    _get_record_key,
    _process_single_row,
    process_rows_with_upsert,
)
from app.db.models.task import Task


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    db.commit = MagicMock()
    db.rollback = MagicMock()
    db.execute = MagicMock()
    return db


@pytest.fixture
def mock_task_insert_only():
    """Mock Task with insert only (no upsert)"""
    task = MagicMock(spec=Task)
    task.id = 1
    task.dest_table = "EMPLOYEES"
    task.upsert_enabled = False
    task.upsert_keys = None
    task.skip_column = None
    task.skip_value = None
    task.continue_on_error = True
    return task


@pytest.fixture
def mock_task_upsert():
    """Mock Task with upsert enabled"""
    task = MagicMock(spec=Task)
    task.id = 1
    task.dest_table = "EMPLOYEES"
    task.upsert_enabled = True
    task.upsert_keys = ["employee_id"]
    task.skip_column = None
    task.skip_value = None
    task.continue_on_error = True
    return task


@pytest.fixture
def mock_task_upsert_with_skip():
    """Mock Task with upsert and skip condition"""
    task = MagicMock(spec=Task)
    task.id = 1
    task.dest_table = "EMPLOYEES"
    task.upsert_enabled = True
    task.upsert_keys = ["employee_id"]
    task.skip_column = "processed"
    task.skip_value = "Y"
    task.continue_on_error = True
    return task


@pytest.fixture
def mock_task_no_continue():
    """Mock Task with continue_on_error = False"""
    task = MagicMock(spec=Task)
    task.id = 1
    task.dest_table = "EMPLOYEES"
    task.upsert_enabled = True
    task.upsert_keys = ["employee_id"]
    task.skip_column = None
    task.skip_value = None
    task.continue_on_error = False
    return task


class TestRowStatus:
    """Tests for RowStatus enum"""

    def test_row_status_values(self):
        """Test RowStatus enum values"""
        assert RowStatus.INSERTED.value == "inserted"
        assert RowStatus.UPDATED.value == "updated"
        assert RowStatus.SKIPPED.value == "skipped"
        assert RowStatus.ERROR.value == "error"


class TestRowResult:
    """Tests for RowResult dataclass"""

    def test_row_result_creation(self):
        """Test RowResult dataclass creation"""
        result = RowResult(
            status=RowStatus.INSERTED, record_key="employee_id=123", message="Success"
        )
        assert result.status == RowStatus.INSERTED
        assert result.record_key == "employee_id=123"
        assert result.message == "Success"

    def test_row_result_default_message(self):
        """Test RowResult default message"""
        result = RowResult(status=RowStatus.SKIPPED, record_key="id=1")
        assert result.message == ""


class TestShouldSkip:
    """Tests for _should_skip function"""

    def test_should_skip_no_skip_column(self, mock_task_upsert):
        """Test _should_skip returns False when no skip_column configured"""
        existing = {"employee_id": 1, "processed": "Y"}
        assert _should_skip(mock_task_upsert, existing) is False

    def test_should_skip_no_skip_value(self, mock_task_upsert_with_skip):
        """Test _should_skip returns False when skip_value is None"""
        mock_task_upsert_with_skip.skip_value = None
        existing = {"employee_id": 1, "processed": "Y"}
        assert _should_skip(mock_task_upsert_with_skip, existing) is False

    def test_should_skip_condition_met_uppercase(self, mock_task_upsert_with_skip):
        """Test _should_skip returns True when condition is met (uppercase)"""
        existing = {"employee_id": 1, "PROCESSED": "Y"}
        assert _should_skip(mock_task_upsert_with_skip, existing) is True

    def test_should_skip_condition_met_lowercase(self, mock_task_upsert_with_skip):
        """Test _should_skip returns True when condition is met (lowercase)"""
        existing = {"employee_id": 1, "processed": "y"}
        assert _should_skip(mock_task_upsert_with_skip, existing) is True

    def test_should_skip_condition_not_met(self, mock_task_upsert_with_skip):
        """Test _should_skip returns False when condition is not met"""
        existing = {"employee_id": 1, "processed": "N"}
        assert _should_skip(mock_task_upsert_with_skip, existing) is False

    def test_should_skip_column_not_exists(self, mock_task_upsert_with_skip):
        """Test _should_skip returns False when column doesn't exist"""
        existing = {"employee_id": 1, "name": "John"}
        assert _should_skip(mock_task_upsert_with_skip, existing) is False

    def test_should_skip_null_value(self, mock_task_upsert_with_skip):
        """Test _should_skip returns False when value is null"""
        existing = {"employee_id": 1, "processed": None}
        assert _should_skip(mock_task_upsert_with_skip, existing) is False


class TestGetRecordKey:
    """Tests for _get_record_key function"""

    def test_get_record_key_with_keys(self):
        """Test _get_record_key with upsert keys"""
        row = {"employee_id": 123, "name": "John", "dept": "IT"}
        key = _get_record_key(row, ["employee_id"])
        assert key == "employee_id=123"

    def test_get_record_key_composite(self):
        """Test _get_record_key with composite keys"""
        row = {"order_id": 1, "product_id": 100, "qty": 5}
        key = _get_record_key(row, ["order_id", "product_id"])
        assert key == "order_id=1, product_id=100"

    def test_get_record_key_no_keys(self):
        """Test _get_record_key with no upsert keys"""
        row = {"name": "John"}
        key = _get_record_key(row, [])
        assert key.startswith("row_")


class TestProcessSingleRow:
    """Tests for _process_single_row function"""

    @patch("app.services.runner._insert_single_row")
    @patch("app.services.runner._find_existing_record")
    def test_insert_when_upsert_disabled(
        self, mock_find, mock_insert, mock_db, mock_task_insert_only
    ):
        """Test INSERT when upsert is disabled"""
        row = {"employee_id": 1, "name": "John"}

        result = _process_single_row(mock_db, mock_task_insert_only, row, 0)

        assert result.status == RowStatus.INSERTED
        mock_insert.assert_called_once()
        mock_find.assert_not_called()

    @patch("app.services.runner._insert_single_row")
    @patch("app.services.runner._find_existing_record")
    def test_insert_when_record_not_exists(self, mock_find, mock_insert, mock_db, mock_task_upsert):
        """Test INSERT when record doesn't exist"""
        mock_find.return_value = None
        row = {"employee_id": 1, "name": "John"}

        result = _process_single_row(mock_db, mock_task_upsert, row, 0)

        assert result.status == RowStatus.INSERTED
        mock_insert.assert_called_once()

    @patch("app.services.runner._update_existing_row")
    @patch("app.services.runner._find_existing_record")
    def test_update_when_record_exists(self, mock_find, mock_update, mock_db, mock_task_upsert):
        """Test UPDATE when record exists"""
        mock_find.return_value = {"employee_id": 1, "name": "Old Name"}
        row = {"employee_id": 1, "name": "New Name"}

        result = _process_single_row(mock_db, mock_task_upsert, row, 0)

        assert result.status == RowStatus.UPDATED
        mock_update.assert_called_once()

    @patch("app.services.runner._find_existing_record")
    def test_skip_when_condition_met(self, mock_find, mock_db, mock_task_upsert_with_skip):
        """Test SKIP when skip condition is met"""
        mock_find.return_value = {"employee_id": 1, "processed": "Y"}
        row = {"employee_id": 1, "name": "John"}

        result = _process_single_row(mock_db, mock_task_upsert_with_skip, row, 0)

        assert result.status == RowStatus.SKIPPED
        assert "Skip condition met" in result.message
        mock_db.commit.assert_not_called()

    @patch("app.services.runner._insert_single_row")
    @patch("app.services.runner._find_existing_record")
    def test_error_on_integrity_error(self, mock_find, mock_insert, mock_db, mock_task_upsert):
        """Test ERROR on IntegrityError (constraint violation)"""
        mock_find.return_value = None
        mock_insert.side_effect = IntegrityError(
            statement="INSERT", params={}, orig=Exception("unique constraint violated")
        )
        row = {"employee_id": 1, "name": "John"}

        result = _process_single_row(mock_db, mock_task_upsert, row, 0)

        assert result.status == RowStatus.ERROR
        assert "Constraint violation" in result.message
        mock_db.rollback.assert_called_once()

    @patch("app.services.runner._insert_single_row")
    @patch("app.services.runner._find_existing_record")
    def test_error_on_database_error(self, mock_find, mock_insert, mock_db, mock_task_upsert):
        """Test ERROR on DatabaseError"""
        mock_find.return_value = None
        mock_insert.side_effect = DatabaseError(
            statement="INSERT", params={}, orig=Exception("connection lost")
        )
        row = {"employee_id": 1, "name": "John"}

        result = _process_single_row(mock_db, mock_task_upsert, row, 0)

        assert result.status == RowStatus.ERROR
        assert "Database error" in result.message
        mock_db.rollback.assert_called_once()


class TestProcessRowsWithUpsert:
    """Tests for process_rows_with_upsert function"""

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_process_all_inserted(self, mock_log_error, mock_process, mock_db, mock_task_upsert):
        """Test all rows inserted successfully"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]
        mock_process.side_effect = [
            RowResult(status=RowStatus.INSERTED, record_key="employee_id=1"),
            RowResult(status=RowStatus.INSERTED, record_key="employee_id=2"),
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, rows)

        assert results["inserted"] == 2
        assert results["updated"] == 0
        assert results["skipped"] == 0
        assert results["errors"] == 0
        mock_log_error.assert_not_called()

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_process_mixed_results(
        self, mock_log_error, mock_process, mock_db, mock_task_upsert_with_skip
    ):
        """Test mixed results: insert, update, skip"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
            {"employee_id": 3, "name": "Charlie"},
        ]
        mock_process.side_effect = [
            RowResult(status=RowStatus.INSERTED, record_key="employee_id=1"),
            RowResult(status=RowStatus.UPDATED, record_key="employee_id=2"),
            RowResult(
                status=RowStatus.SKIPPED,
                record_key="employee_id=3",
                message="Already processed",
            ),
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert_with_skip, 1, rows)

        assert results["inserted"] == 1
        assert results["updated"] == 1
        assert results["skipped"] == 1
        assert results["errors"] == 0

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_continue_on_error(self, mock_log_error, mock_process, mock_db, mock_task_upsert):
        """Test processing continues when error occurs (continue_on_error=True)"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
            {"employee_id": 3, "name": "Charlie"},
        ]
        mock_process.side_effect = [
            RowResult(status=RowStatus.INSERTED, record_key="employee_id=1"),
            RowResult(
                status=RowStatus.ERROR,
                record_key="employee_id=2",
                message="Constraint error",
            ),
            RowResult(status=RowStatus.INSERTED, record_key="employee_id=3"),
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, rows)

        # All rows should be processed despite error
        assert results["inserted"] == 2
        assert results["errors"] == 1
        assert len(results["error_details"]) == 1
        assert results["error_details"][0]["row_index"] == 1
        mock_log_error.assert_called_once()

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_stop_on_error_when_disabled(
        self, mock_log_error, mock_process, mock_db, mock_task_no_continue
    ):
        """Test processing stops when error occurs and continue_on_error=False"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]
        mock_process.side_effect = Exception("Unexpected error")

        with pytest.raises(Exception, match="Unexpected error"):
            process_rows_with_upsert(mock_db, mock_task_no_continue, 1, rows)

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_empty_rows(self, mock_log_error, mock_process, mock_db, mock_task_upsert):
        """Test processing empty rows list"""
        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, [])

        assert results["inserted"] == 0
        assert results["updated"] == 0
        assert results["skipped"] == 0
        assert results["errors"] == 0
        mock_process.assert_not_called()

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_all_rows_skipped(
        self, mock_log_error, mock_process, mock_db, mock_task_upsert_with_skip
    ):
        """Test all rows skipped due to skip condition"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]
        mock_process.side_effect = [
            RowResult(
                status=RowStatus.SKIPPED,
                record_key="employee_id=1",
                message="processed=Y",
            ),
            RowResult(
                status=RowStatus.SKIPPED,
                record_key="employee_id=2",
                message="processed=Y",
            ),
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert_with_skip, 1, rows)

        assert results["inserted"] == 0
        assert results["updated"] == 0
        assert results["skipped"] == 2
        assert results["errors"] == 0

    @patch("app.services.runner._process_single_row")
    @patch("app.services.runner.log_row_error")
    def test_all_rows_error(self, mock_log_error, mock_process, mock_db, mock_task_upsert):
        """Test all rows have errors but processing continues"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]
        mock_process.side_effect = [
            RowResult(status=RowStatus.ERROR, record_key="employee_id=1", message="Error 1"),
            RowResult(status=RowStatus.ERROR, record_key="employee_id=2", message="Error 2"),
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, rows)

        assert results["inserted"] == 0
        assert results["updated"] == 0
        assert results["errors"] == 2
        assert len(results["error_details"]) == 2
        assert mock_log_error.call_count == 2


class TestUpsertIntegration:
    """Integration tests for upsert flow"""

    @patch("app.services.runner._find_existing_record")
    @patch("app.services.runner._insert_single_row")
    @patch("app.services.runner._update_existing_row")
    @patch("app.services.runner.log_row_error")
    def test_full_upsert_flow(
        self,
        mock_log_error,
        mock_update,
        mock_insert,
        mock_find,
        mock_db,
        mock_task_upsert_with_skip,
    ):
        """Test complete upsert flow with mixed scenarios"""
        rows = [
            {"employee_id": 1, "name": "New Employee"},  # Will INSERT
            {"employee_id": 2, "name": "Updated Employee"},  # Will UPDATE
            {"employee_id": 3, "name": "Processed Employee"},  # Will SKIP
        ]

        # Mock find results
        mock_find.side_effect = [
            None,  # Row 1: not found -> INSERT
            {
                "employee_id": 2,
                "name": "Old",
                "processed": "N",
            },  # Row 2: found, not processed -> UPDATE
            {
                "employee_id": 3,
                "name": "Old",
                "processed": "Y",
            },  # Row 3: found, processed -> SKIP
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert_with_skip, 1, rows)

        assert results["inserted"] == 1
        assert results["updated"] == 1
        assert results["skipped"] == 1
        assert results["errors"] == 0
        mock_insert.assert_called_once()
        mock_update.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
