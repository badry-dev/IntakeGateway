"""Tests for v1.4 phase 3 performance & reliability changes."""

import json
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

from app.db.models.column_mapping import ColumnMapping
from app.db.models.task import Task
from app.services.mapper import map_rows


class TestTransformParsingHoist:
    """json.loads must run once per mapping, not once per row (v1.4 task 14)."""

    def _mappings(self, n=20):
        mappings = []
        for i in range(n):
            m = MagicMock(spec=ColumnMapping)
            m.is_active = True
            m.source_field = f"src_{i}"
            m.dest_column = f"dest_{i}"
            m.transform_rules = json.dumps(["trim", "upper"])
            mappings.append(m)
        return mappings

    def test_json_parsed_once_per_mapping(self):
        rows = [{f"src_{i}": f"  value-{r}-{i} " for i in range(20)} for r in range(1000)]
        mappings = self._mappings(20)

        with patch("app.services.mapper.json.loads", wraps=json.loads) as spy:
            result = map_rows(rows, mappings)

        # 20 mappings x (1 parse each) — NOT rows x mappings (20,000)
        assert spy.call_count == 20
        assert len(result) == 1000
        assert result[0]["dest_0"] == "VALUE-0-0"

    def test_inactive_mappings_excluded(self):
        rows = [{"a": " x ", "b": " y "}]
        active = MagicMock(spec=ColumnMapping)
        active.is_active = True
        active.source_field = "a"
        active.dest_column = "col_a"
        active.transform_rules = None

        inactive = MagicMock(spec=ColumnMapping)
        inactive.is_active = False
        inactive.source_field = "b"
        inactive.dest_column = "col_b"
        inactive.transform_rules = json.dumps(["upper"])

        result = map_rows(rows, [active, inactive])
        assert result[0] == {"col_a": " x "}


class TestBatchFallbackToRowByRow:
    """A failing bulk statement must roll back to a savepoint and fall back to
    per-row processing without replaying partial writes (v1.4 H5 / task 18)."""

    TWO_COL_DDL = 'CREATE TABLE "EMPLOYEES" ("employee_id" INTEGER PRIMARY KEY, "name" TEXT)'

    @pytest.fixture
    def sqlite_dest(self, sqlite_dest_factory):
        return sqlite_dest_factory(self.TWO_COL_DDL)

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

    def test_successful_bulk_path_commits_once(self, sqlite_dest_factory, task):
        """No mocks: new rows only — the savepoint bulk path commits and no
        fallback warning runs."""
        from app.services.runner import process_rows_with_upsert

        db = sqlite_dest_factory(self.TWO_COL_DDL)
        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
        ]

        with patch("app.services.runner.logger.warning") as mock_warn:
            results = process_rows_with_upsert(db, task, 1, rows, app_db=db)

        assert results["inserted"] == 2
        assert results["updated"] == 0
        assert results["errors"] == 0
        mock_warn.assert_not_called()

        # Rows are committed (visible on a fresh session)
        names = {
            r[0]: r[1] for r in db.execute(text('SELECT "employee_id", "name" FROM "EMPLOYEES"'))
        }
        assert names == {1: "Alice", 2: "Bob"}

    def test_bulk_failure_falls_back_per_row(self, sqlite_dest, task):
        from app.services.runner import process_rows_with_upsert

        # Row 1 exists -> routed to to_update; rows 2/3 are new.
        sqlite_dest.execute(text("INSERT INTO \"EMPLOYEES\" VALUES (1, 'Old')"))
        sqlite_dest.commit()

        rows = [
            {"employee_id": 1, "name": "Alice"},
            {"employee_id": 2, "name": "Bob"},
            {"employee_id": 3, "name": "Charlie"},
        ]

        with patch("app.services.runner._bulk_update_rows") as mock_bulk:
            mock_bulk.side_effect = RuntimeError("simulated bulk failure")

            results = process_rows_with_upsert(sqlite_dest, task, 1, rows, app_db=sqlite_dest)

        assert results["updated"] == 1
        assert results["inserted"] == 2
        assert results["errors"] == 0

        names = {
            r[0]: r[1]
            for r in sqlite_dest.execute(text('SELECT "employee_id", "name" FROM "EMPLOYEES"'))
        }
        assert names == {1: "Alice", 2: "Bob", 3: "Charlie"}

    def test_insert_failure_inside_savepoint_falls_back_per_row(self, sqlite_dest, task):
        """A REAL failure of the insert statement inside the savepoint (not a
        mocked helper): partial updates staged before it are rolled back and
        every row is recovered by the per-row fallback."""
        from app.services.runner import process_rows_with_upsert

        # Row 2 already exists -> the bulk INSERT chunk violates the PK.
        sqlite_dest.execute(text('INSERT INTO "EMPLOYEES" ("employee_id") VALUES (2)'))
        sqlite_dest.commit()

        rows = [
            {"employee_id": 1, "name": "New"},
            {"employee_id": 2, "name": "Clash"},  # PK violation on bulk insert
            {"employee_id": 3, "name": "Also New"},
        ]

        results = process_rows_with_upsert(sqlite_dest, task, 1, rows, app_db=sqlite_dest)

        assert results["errors"] == 0
        names = {
            r[0]: r[1]
            for r in sqlite_dest.execute(text('SELECT "employee_id", "name" FROM "EMPLOYEES"'))
        }
        # All three rows landed exactly once via per-row fallback
        assert names[1] == "New"
        assert names[2] == "Clash"
        assert names[3] == "Also New"
        assert len(names) == 3

    def test_no_duplicate_writes_after_fallback(self, sqlite_dest, task):
        from app.services.runner import process_rows_with_upsert

        rows = [{"employee_id": 1, "name": "Only"}]
        sqlite_dest.execute(
            text('INSERT INTO "EMPLOYEES" ("employee_id", "name") VALUES (1, \'Existing\')')
        )
        sqlite_dest.commit()

        with (
            patch("app.services.runner.insert_batch") as mock_insert_batch,
            patch("app.services.runner._bulk_update_rows") as mock_bulk,
        ):
            mock_bulk.side_effect = RuntimeError("boom")

            process_rows_with_upsert(sqlite_dest, task, 1, rows, app_db=sqlite_dest)

        # Record-then-assert: a side_effect AssertionError would be swallowed
        # by the batch-level except and silently pass.
        mock_insert_batch.assert_not_called()

        count = sqlite_dest.execute(
            text('SELECT COUNT(*) FROM "EMPLOYEES" WHERE "employee_id" = 1')
        ).scalar()
        assert count == 1
        name = sqlite_dest.execute(
            text('SELECT "name" FROM "EMPLOYEES" WHERE "employee_id" = 1')
        ).scalar()
        assert name == "Only"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
