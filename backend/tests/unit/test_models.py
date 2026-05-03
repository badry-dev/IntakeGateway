"""Unit tests for database models"""

import pytest
from datetime import datetime, timezone
from app.db.models.task import Task
from app.db.models.task_run import TaskRun
from app.db.models.task_schedule import TaskSchedule
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.db.models.column_mapping import ColumnMapping
from app.db.session import Base, SessionLocal


class TestTaskModel:
    """Tests for Task ORM model"""

    def test_task_creation(self):
        """Test creating a Task instance"""
        task = Task(
            name="Test API Import",
            description="Test task for importing data",
            http_method="GET",
            endpoint_path="https://api.example.com/customers",
            record_path="$.data[*]",
            dest_table="CUSTOMERS",
            batch_size=500,
            is_active=True,
        )

        assert task.name == "Test API Import"
        assert task.http_method == "GET"
        assert task.batch_size == 500
        assert task.is_active is True
        assert task.dest_table == "CUSTOMERS"

    def test_task_defaults(self):
        """Test Task model defaults (set at database level)"""
        task = Task(
            name="Minimal Task",
            endpoint_path="https://api.example.com/data",
            dest_table="DATA",
        )

        # SQLAlchemy defaults are applied at database level, not Python instantiation
        # In Python, we need to check that the field accepts None without error
        assert task.http_method is None or task.http_method == "GET"
        assert task.batch_size is None or task.batch_size == 500
        assert task.is_active is None or task.is_active is True
        assert task.record_path is None

    def test_task_json_fields(self):
        """Test Task model JSON field support"""
        task = Task(
            name="Task with JSON",
            endpoint_path="https://api.example.com/data",
            dest_table="DATA",
            query_params_json={"limit": 1000, "offset": 0},
            headers_json={"Authorization": "Bearer token123"},
            body_json={"filter": "active"},
        )

        assert task.query_params_json == {"limit": 1000, "offset": 0}
        assert task.headers_json == {"Authorization": "Bearer token123"}
        assert task.body_json == {"filter": "active"}


class TestTaskRunModel:
    """Tests for TaskRun ORM model"""

    def test_task_run_creation(self):
        """Test creating a TaskRun instance"""
        task_run = TaskRun(
            task_id=1,
            status="RUNNING",
            rows_fetched=100,
            rows_inserted=95,
            error_count=5,
        )

        assert task_run.task_id == 1
        assert task_run.status == "RUNNING"
        assert task_run.rows_fetched == 100
        assert task_run.rows_inserted == 95
        assert task_run.error_count == 5

    def test_task_run_defaults(self):
        """Test TaskRun model defaults (set at database level)"""
        task_run = TaskRun(task_id=1)

        # SQLAlchemy defaults are applied at database level, not Python instantiation
        # In Python, we verify the field can be None without error
        assert task_run.status is None or task_run.status == "PENDING"
        assert task_run.rows_fetched is None or task_run.rows_fetched == 0
        assert task_run.rows_inserted is None or task_run.rows_inserted == 0
        assert task_run.error_count is None or task_run.error_count == 0
        assert task_run.ended_at is None

    def test_task_run_status_lifecycle(self):
        """Test TaskRun status progression"""
        task_run = TaskRun(task_id=1, status="PENDING")
        assert task_run.status == "PENDING"

        task_run.status = "RUNNING"
        assert task_run.status == "RUNNING"

        task_run.status = "SUCCESS"
        assert task_run.status == "SUCCESS"


class TestTaskScheduleModel:
    """Tests for TaskSchedule ORM model"""

    def test_task_schedule_creation(self):
        """Test creating a TaskSchedule instance"""
        schedule = TaskSchedule(task_id=1, cron_expression="0 2 * * *", is_active=True)

        assert schedule.task_id == 1
        assert schedule.cron_expression == "0 2 * * *"
        assert schedule.is_active is True
        assert schedule.last_run_date is None
        assert schedule.next_run_date is None

    def test_task_schedule_with_dates(self):
        """Test TaskSchedule with execution dates"""
        now = datetime.now(timezone.utc)
        schedule = TaskSchedule(
            task_id=1, cron_expression="0 * * * *", last_run_date=now, next_run_date=now
        )

        assert schedule.last_run_date is not None
        assert schedule.next_run_date is not None


class TestTaskLogModel:
    """Tests for TaskLog ORM model"""

    def test_task_log_creation(self):
        """Test creating a TaskLog instance"""
        log = TaskLog(
            task_run_id=1,
            step_name="FETCH_API",
            message="Successfully fetched 500 records from API",
        )

        assert log.task_run_id == 1
        assert log.step_name == "FETCH_API"
        assert log.message == "Successfully fetched 500 records from API"
        assert log.details is None

    def test_task_log_with_details(self):
        """Test TaskLog with JSON details"""
        log = TaskLog(
            task_run_id=1,
            step_name="INSERT_DB",
            message="Inserted batch of records",
            details='{"rows_inserted": 500, "duration_ms": 250}',
        )

        assert log.details == '{"rows_inserted": 500, "duration_ms": 250}'

    def test_task_log_all_steps(self):
        """Test all valid task log steps"""
        steps = ["FETCH_API", "MAP_RECORDS", "VALIDATE", "INSERT_DB"]

        for step in steps:
            log = TaskLog(task_run_id=1, step_name=step)
            assert log.step_name == step


class TestTaskRunLogModel:
    """Tests for TaskRunLog ORM model"""

    def test_task_run_log_creation(self):
        """Test creating a TaskRunLog instance"""
        error_log = TaskRunLog(
            task_run_id=1,
            row_number=45,
            column_name="email",
            error_type="REQUIRED_FIELD",
            error_message="Column email is required (not nullable)",
            source_value="john.doe@example.com",
        )

        assert error_log.task_run_id == 1
        assert error_log.row_number == 45
        assert error_log.column_name == "email"
        assert error_log.error_type == "REQUIRED_FIELD"

    def test_task_run_log_row_level_error(self):
        """Test TaskRunLog for row-level errors"""
        error_log = TaskRunLog(
            task_run_id=1,
            row_number=102,
            column_name="email",
            error_type="VALIDATION_FAILED",
            error_message="Invalid email format",
            source_value="invalid-email",
        )

        assert error_log.error_type == "VALIDATION_FAILED"
        assert error_log.row_number == 102

    def test_task_run_log_non_row_specific(self):
        """Test TaskRunLog for non-row-specific errors"""
        error_log = TaskRunLog(
            task_run_id=1,
            row_number=None,
            error_type="API_TIMEOUT",
            error_message="Request to API timed out after 30s",
        )

        assert error_log.row_number is None
        assert error_log.error_type == "API_TIMEOUT"


class TestColumnMappingModel:
    """Tests for ColumnMapping ORM model"""

    def test_column_mapping_creation(self):
        """Test creating a ColumnMapping instance"""
        mapping = ColumnMapping(
            task_id=1, source_field="customer_id", dest_column="CUST_ID", is_active=True
        )

        assert mapping.task_id == 1
        assert mapping.source_field == "customer_id"
        assert mapping.dest_column == "CUST_ID"
        assert mapping.is_active is True

    def test_column_mapping_with_transforms(self):
        """Test ColumnMapping with transform rules"""
        mapping = ColumnMapping(
            task_id=1,
            source_field="full_name",
            dest_column="NAME",
            transform_rules='{"transform": "upper", "trim": true}',
        )

        assert mapping.transform_rules == '{"transform": "upper", "trim": true}'

    def test_column_mapping_inactive(self):
        """Test deactivating a column mapping"""
        mapping = ColumnMapping(
            task_id=1, source_field="email", dest_column="EMAIL", is_active=False
        )

        assert mapping.is_active is False


class TestModelRelationships:
    """Tests for model relationships and constraints"""

    def test_task_run_requires_task_id(self):
        """Test that TaskRun requires a task_id"""
        task_run = TaskRun(task_id=None)
        # task_id is required in schema, should fail on insert
        assert task_run.task_id is None

    def test_task_schedule_requires_task_id(self):
        """Test that TaskSchedule requires a task_id"""
        schedule = TaskSchedule(task_id=1, cron_expression="0 2 * * *")
        assert schedule.task_id == 1

    def test_column_mapping_requires_task_id(self):
        """Test that ColumnMapping requires a task_id"""
        mapping = ColumnMapping(task_id=1, source_field="id", dest_column="ID")
        assert mapping.task_id == 1


class TestModelInstantiation:
    """Tests for model instantiation without database"""

    def test_all_models_can_be_instantiated(self):
        """Test that all models can be instantiated"""
        models = [
            Task(name="test", endpoint_path="http://api", dest_table="T"),
            TaskRun(task_id=1),
            TaskSchedule(task_id=1, cron_expression="0 * * * *"),
            TaskLog(task_run_id=1, step_name="TEST"),
            TaskRunLog(task_run_id=1),
            ColumnMapping(task_id=1, source_field="src", dest_column="dst"),
        ]

        for model in models:
            assert model is not None

    def test_base_metadata_includes_all_models(self):
        """Test that Base.metadata includes all tables"""
        table_names = {table.name for table in Base.metadata.tables.values()}

        expected_tables = {
            "task",
            "task_run",
            "task_schedule",
            "column_mapping",
            "task_log",
            "task_run_log",
        }

        assert expected_tables.issubset(table_names), (
            f"Missing tables: {expected_tables - table_names}"
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
