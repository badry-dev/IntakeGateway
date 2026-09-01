"""Unit tests for upsert and skip logic in runner service (Phase 8)"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.db.models.task import Task
from app.services.runner import (
    RowResult,
    RowStatus,
    _bulk_update_rows,
    _get_record_key,
    _process_single_row,
    _should_skip,
    process_rows_with_upsert,
)


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
    """Tests for the batched process_rows_with_upsert implementation"""

    @patch("app.services.runner._process_upsert_batch")
    def test_process_all_inserted(self, mock_batch, mock_db, mock_task_upsert):
        """Test all rows inserted successfully"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]
        mock_batch.return_value = {
            "inserted": 2,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
        }

        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, rows)

        assert results["inserted"] == 2
        assert results["updated"] == 0
        assert results["skipped"] == 0
        assert results["errors"] == 0
        assert mock_batch.call_count == 1

    @patch("app.services.runner._process_upsert_batch")
    def test_process_mixed_results(self, mock_batch, mock_db, mock_task_upsert_with_skip):
        """Test mixed results: insert, update, skip are aggregated across batches"""
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
            {"employee_id": 3, "name": "Charlie"},
        ]
        mock_batch.return_value = {
            "inserted": 1,
            "updated": 1,
            "skipped": 1,
            "errors": 0,
            "error_details": [],
        }

        results = process_rows_with_upsert(mock_db, mock_task_upsert_with_skip, 1, rows)

        assert results["inserted"] == 1
        assert results["updated"] == 1
        assert results["skipped"] == 1
        assert results["errors"] == 0

    @patch("app.services.runner._process_upsert_batch")
    def test_continue_on_error(self, mock_batch, mock_db, mock_task_upsert):
        """Test processing continues when a batch errors (continue_on_error=True)"""
        rows = [
            {"employee_id": i, "name": f"Person {i}"} for i in range(1, 1001)
        ]  # two batches of 500
        mock_batch.side_effect = [
            {
                "inserted": 500,
                "updated": 0,
                "skipped": 0,
                "errors": 0,
                "error_details": [],
            },
            {
                "inserted": 400,
                "updated": 0,
                "skipped": 0,
                "errors": 100,
                "error_details": [{"batch_start": 500, "batch_size": 500, "error": "boom"}],
            },
        ]

        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, rows)

        # Second batch failure must not abort aggregation
        assert results["inserted"] == 900
        assert results["errors"] == 100
        assert len(results["error_details"]) == 1
        assert mock_batch.call_count == 2

    @patch("app.services.runner._process_upsert_batch")
    def test_empty_rows(self, mock_batch, mock_db, mock_task_upsert):
        """Test processing empty rows list"""
        results = process_rows_with_upsert(mock_db, mock_task_upsert, 1, [])

        assert results["inserted"] == 0
        assert results["updated"] == 0
        assert results["skipped"] == 0
        assert results["errors"] == 0
        mock_batch.assert_not_called()

    @patch("app.services.runner._process_upsert_batch")
    def test_no_upsert_keys_falls_back_to_insert(self, mock_batch, mock_db, mock_task_insert_only):
        """No upsert keys configured -> bulk insert path, no batch upsert"""
        rows = [{"employee_id": 1, "name": "Alice"}]

        with patch("app.services.runner.insert_batch", return_value=1) as mock_insert:
            results = process_rows_with_upsert(mock_db, mock_task_insert_only, 1, rows)

        assert results["inserted"] == 1
        mock_insert.assert_called_once()
        mock_batch.assert_not_called()


class TestBulkUpdateNullPreservation:
    """Regression tests for the bulk CASE-UPDATE NULL corruption (v1.4 C2).

    These run real SQL against an in-memory SQLite destination. The generated
    statements use double-quoted identifiers and plain binds (no TO_DATE unless
    a YYYY-MM-DD string is present), so they execute on SQLite.
    """

    @pytest.fixture
    def sqlite_dest(self, sqlite_dest_factory):
        return sqlite_dest_factory(
            'CREATE TABLE "EMPLOYEES" ("employee_id" INTEGER PRIMARY KEY, "name" TEXT)'
        )

    @pytest.fixture
    def task(self):
        task = MagicMock(spec=Task)
        task.id = 1
        task.dest_table = "EMPLOYEES"
        task.upsert_enabled = True
        task.upsert_keys = ["employee_id"]
        task.skip_column = None
        task.skip_value = None
        return task

    def _seed(self, db, employee_id, name):
        from sqlalchemy import text

        db.execute(
            text('INSERT INTO "EMPLOYEES" ("employee_id", "name") VALUES (:i, :n)'),
            {"i": employee_id, "n": name},
        )
        db.commit()

    def _fetch_name(self, db, employee_id):
        from sqlalchemy import text

        result = db.execute(
            text('SELECT "name" FROM "EMPLOYEES" WHERE "employee_id" = :i'),
            {"i": employee_id},
        ).scalar()
        return result

    def test_none_value_preserves_existing_column(self, sqlite_dest, task):
        """A None in the incoming row must NOT overwrite the stored value."""
        self._seed(sqlite_dest, 1, "Original")

        to_update = [(0, {"employee_id": 1, "name": None})]
        count = _bulk_update_rows(sqlite_dest, task, to_update, ["employee_id"])

        # Every value for every column is None -> no SET clauses are emitted
        # (count 0), which trivially preserves the stored value.
        assert count == 0
        assert self._fetch_name(sqlite_dest, 1) == "Original"

    def test_non_none_value_is_written(self, sqlite_dest, task):
        self._seed(sqlite_dest, 1, "Original")

        to_update = [(0, {"employee_id": 1, "name": "Updated"})]
        _bulk_update_rows(sqlite_dest, task, to_update, ["employee_id"])

        assert self._fetch_name(sqlite_dest, 1) == "Updated"

    def test_heterogeneous_batch_mixed_nulls(self, sqlite_dest, task):
        """Mixed batch: non-None values written, None values preserved."""
        self._seed(sqlite_dest, 1, "Keep-Me")
        self._seed(sqlite_dest, 2, "Old-Name")

        to_update = [
            (0, {"employee_id": 1, "name": "New-Name"}),
            (1, {"employee_id": 2, "name": None}),
        ]
        _bulk_update_rows(sqlite_dest, task, to_update, ["employee_id"])

        assert self._fetch_name(sqlite_dest, 1) == "New-Name"
        assert self._fetch_name(sqlite_dest, 2) == "Old-Name"

    def test_column_present_only_in_later_row_is_updated(self, sqlite_dest, task):
        """update_cols must be a union across all rows, not first-row only.

        Row 1 lacks `name` entirely; row 2 has it. Both must be handled.
        """
        from sqlalchemy import text

        sqlite_dest.execute(text('ALTER TABLE "EMPLOYEES" ADD COLUMN "email" TEXT'))
        self._seed(sqlite_dest, 1, "Row One")
        self._seed(sqlite_dest, 2, "Row Two")

        to_update = [
            (0, {"employee_id": 1}),  # no name/email keys at all
            (1, {"employee_id": 2, "email": "row2@example.com"}),
        ]
        count = _bulk_update_rows(sqlite_dest, task, to_update, ["employee_id"])

        assert count >= 1
        email_val = sqlite_dest.execute(
            text('SELECT "email" FROM "EMPLOYEES" WHERE "employee_id" = :i'), {"i": 2}
        ).scalar()
        assert email_val == "row2@example.com"


class TestDuplicateUpsertKeysInBatch:
    """Duplicate upsert-key tuples within one batch: first occurrence wins,
    duplicates are counted as skipped (v1.4 review finding)."""

    @pytest.fixture
    def task(self):
        task = MagicMock(spec=Task)
        task.id = 1
        task.dest_table = "EMPLOYEES"
        task.upsert_enabled = True
        task.upsert_keys = ["employee_id"]
        task.skip_column = None
        task.skip_value = None
        return task

    def test_duplicate_keys_first_row_wins(self, task):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []  # nothing exists

        rows = [
            {"employee_id": 1, "name": "First"},
            {"employee_id": 1, "name": "Second"},  # duplicate key
        ]
        with patch("app.services.runner.insert_batch", return_value=1):
            results = process_rows_with_upsert(db, task, 1, rows)

        assert results["inserted"] == 1
        assert results["skipped"] == 1
        assert any(
            "duplicate upsert key" in str(d.get("error", "")) for d in results["error_details"]
        )

    def test_rows_without_key_values_are_not_collapsed(self, task):
        """Rows lacking the upsert key cannot collide on it; they must not be
        folded into one 'duplicate' — the pre-dedupe behaviour (insert) stands."""
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []

        rows = [{"name": "A"}, {"name": "B"}]
        results = process_rows_with_upsert(db, task, 1, rows)

        assert results["skipped"] == 0
        assert results["inserted"] == 2
        assert not any("duplicate" in str(d.get("error", "")) for d in results["error_details"])

    def test_duplicate_report_uses_the_callers_row_index(self, task):
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = []

        rows = [
            {"employee_id": 1, "name": "First"},
            {"employee_id": 1, "name": "Dup"},  # index 1
            {"employee_id": 2, "name": "Other"},  # must still be attributed as index 2
        ]
        results = process_rows_with_upsert(db, task, 1, rows)

        dups = [d for d in results["error_details"] if "duplicate" in str(d.get("error", ""))]
        assert [d["row_index"] for d in dups] == [1]
        assert results["inserted"] == 2


class TestBatchSkipCondition:
    """Regression tests for the unimplemented skip condition in the batch
    upsert path (v1.4 C3)."""

    @pytest.fixture
    def sqlite_dest(self, sqlite_dest_factory):
        return sqlite_dest_factory(
            'CREATE TABLE "EMPLOYEES" '
            '("employee_id" INTEGER PRIMARY KEY, "name" TEXT, "processed" TEXT)'
        )

    @pytest.fixture
    def task_with_skip(self):
        task = MagicMock(spec=Task)
        task.id = 1
        task.dest_table = "EMPLOYEES"
        task.upsert_enabled = True
        task.upsert_keys = ["employee_id"]
        task.skip_column = "processed"
        task.skip_value = "Y"
        return task

    def _seed(self, db, employee_id, name, processed):
        from sqlalchemy import text

        db.execute(
            text(
                'INSERT INTO "EMPLOYEES" ("employee_id", "name", "processed") VALUES (:i, :n, :p)'
            ),
            {"i": employee_id, "n": name, "p": processed},
        )
        db.commit()

    def _fetch_name(self, db, employee_id):
        from sqlalchemy import text

        return db.execute(
            text('SELECT "name" FROM "EMPLOYEES" WHERE "employee_id" = :i'),
            {"i": employee_id},
        ).scalar()

    def test_row_marked_processed_is_skipped(self, sqlite_dest, task_with_skip):
        """An existing row whose skip column matches is never overwritten."""
        self._seed(sqlite_dest, 1, "Already Processed", "Y")
        self._seed(sqlite_dest, 2, "Stale", "N")

        rows = [
            {"employee_id": 1, "name": "Overwrite Attempt", "processed": "Y"},
            {"employee_id": 2, "name": "Fresh Value", "processed": "N"},
        ]
        results = process_rows_with_upsert(sqlite_dest, task_with_skip, 1, rows, app_db=sqlite_dest)

        assert results["skipped"] == 1
        assert results["updated"] == 1
        assert self._fetch_name(sqlite_dest, 1) == "Already Processed"
        assert self._fetch_name(sqlite_dest, 2) == "Fresh Value"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


def test_none_column_preserved_while_sibling_column_updates(sqlite_dest_factory):
    """Exercise the ``ELSE <col>`` branch of the bulk CASE update.

    A row with one None column and one non-None column must emit a SET clause
    (so the CASE actually executes) and still keep the stored value for the
    None column.
    """
    from unittest.mock import MagicMock

    from sqlalchemy import text

    from app.services.runner import _bulk_update_rows

    session = sqlite_dest_factory(
        "CREATE TABLE EMPLOYEES (employee_id INTEGER PRIMARY KEY, name TEXT, dept TEXT)"
    )
    session.execute(
        text("INSERT INTO EMPLOYEES (employee_id, name, dept) VALUES (1, 'Original', 'OldDept')")
    )
    session.commit()

    task = MagicMock()
    task.dest_table = "EMPLOYEES"
    task.upsert_keys = ["employee_id"]

    count = _bulk_update_rows(
        session, task, [(0, {"employee_id": 1, "name": None, "dept": "NewDept"})], ["employee_id"]
    )
    session.commit()

    row = session.execute(text("SELECT name, dept FROM EMPLOYEES WHERE employee_id = 1")).fetchone()
    assert count == 1
    assert tuple(row) == ("Original", "NewDept")
