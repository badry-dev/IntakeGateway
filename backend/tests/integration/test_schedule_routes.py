"""Integration tests for schedule API routes"""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.models.task import Task
from app.db.models.task_schedule import TaskSchedule
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


@pytest.fixture
def db():
    """Create a fresh database session for each test, with cleanup after."""
    db = SessionLocal()
    yield db
    try:
        db.query(TaskSchedule).delete()
        db.query(Task).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def sample_task(db: Session):
    """Create a sample task for testing"""
    task = Task(
        name="test-task-schedule",
        description="Task for schedule testing",
        http_method="GET",
        endpoint_path="https://api.example.com/data",
        dest_table="target_table",
        is_active=True,
        auth_type="none",
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


class TestCreateSchedule:
    """Test schedule creation"""

    def test_create_valid_schedule(self, sample_task, db: Session):
        """Test creating a schedule with valid cron expression"""
        payload = {
            "cron_expression": "0 2 * * *",  # Daily at 2 AM
            "is_active": True,
        }

        response = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["task_id"] == sample_task.id
        assert data["cron_expression"] == "0 2 * * *"
        assert data["is_active"] is True
        assert data["next_run_date"] is not None

    def test_create_schedule_task_not_found(self):
        """Test creating schedule for non-existent task"""
        payload = {"cron_expression": "0 2 * * *", "is_active": True}

        response = client.post("/api/v1/tasks/999999/schedule", json=payload)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_create_schedule_invalid_cron(self, sample_task):
        """Test creating schedule with invalid cron expression"""
        payload = {"cron_expression": "invalid cron", "is_active": True}

        response = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)

        assert response.status_code == 422  # Validation error

    def test_create_schedule_duplicate_for_same_task(self, sample_task, db: Session):
        """Test that only one schedule can exist per task"""
        payload = {"cron_expression": "0 2 * * *", "is_active": True}

        # Create first schedule
        response1 = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)
        assert response1.status_code == 201

        # Try to create second schedule for same task
        response2 = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)
        assert response2.status_code == 400
        assert "already has" in response2.json()["detail"].lower()

    def test_create_schedule_hourly(self, sample_task):
        """Test creating hourly schedule"""
        payload = {
            "cron_expression": "0 * * * *",  # Every hour
            "is_active": True,
        }

        response = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["cron_expression"] == "0 * * * *"

    def test_create_schedule_weekly(self, sample_task):
        """Test creating weekly schedule"""
        payload = {
            "cron_expression": "0 2 * * 0",  # Weekly on Sunday at 2 AM
            "is_active": True,
        }

        response = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["cron_expression"] == "0 2 * * 0"

    def test_create_schedule_monthly(self, sample_task):
        """Test creating monthly schedule"""
        payload = {
            "cron_expression": "0 2 1 * *",  # Monthly on 1st at 2 AM
            "is_active": True,
        }

        response = client.post(f"/api/v1/tasks/{sample_task.id}/schedule", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["cron_expression"] == "0 2 1 * *"


class TestGetSchedule:
    """Test schedule retrieval"""

    def test_get_schedule_exists(self, sample_task, db: Session):
        """Test getting an existing schedule"""
        # Create schedule
        schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=True,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        response = client.get(f"/api/v1/tasks/{sample_task.id}/schedule")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == schedule.id
        assert data["cron_expression"] == "0 2 * * *"

    def test_get_schedule_not_found(self, sample_task):
        """Test getting schedule that doesn't exist"""
        response = client.get(f"/api/v1/tasks/{sample_task.id}/schedule")

        assert response.status_code == 404
        assert "no schedule" in response.json()["detail"].lower()

    def test_get_schedule_task_not_found(self):
        """Test getting schedule for non-existent task"""
        response = client.get("/api/v1/tasks/999999/schedule")

        assert response.status_code == 404


class TestUpdateSchedule:
    """Test schedule updates"""

    def test_update_cron_expression(self, sample_task, db: Session):
        """Test updating cron expression"""
        # Create schedule
        schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=True,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        payload = {"cron_expression": "0 3 * * *"}  # Change to 3 AM

        response = client.put(f"/api/v1/schedules/{schedule.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["cron_expression"] == "0 3 * * *"
        assert data["next_run_date"] is not None

    def test_update_active_status(self, sample_task, db: Session):
        """Test toggling active status"""
        # Create schedule
        schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=True,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        payload = {"is_active": False}

        response = client.put(f"/api/v1/schedules/{schedule.id}", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False

    def test_update_schedule_not_found(self):
        """Test updating non-existent schedule"""
        payload = {"cron_expression": "0 3 * * *"}

        response = client.put("/api/v1/schedules/999999", json=payload)

        assert response.status_code == 404


class TestDeleteSchedule:
    """Test schedule deletion"""

    def test_delete_schedule(self, sample_task, db: Session):
        """Test deleting a schedule"""
        # Create schedule
        schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=True,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)
        schedule_id = schedule.id

        response = client.delete(f"/api/v1/schedules/{schedule_id}")

        assert response.status_code == 204

        # Verify schedule is deleted
        deleted_schedule = db.query(TaskSchedule).filter(TaskSchedule.id == schedule_id).first()
        assert deleted_schedule is None

    def test_delete_schedule_not_found(self):
        """Test deleting non-existent schedule"""
        response = client.delete("/api/v1/schedules/999999")

        assert response.status_code == 404


class TestListSchedules:
    """Test schedule listing"""

    def test_list_schedules_empty(self):
        """Test listing schedules when none exist"""
        response = client.get("/api/v1/schedules/")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0
        assert len(data["schedules"]) == 0

    def test_list_schedules_with_pagination(self, sample_task, db: Session):
        """Test listing schedules with pagination"""
        # Create multiple schedules
        for i in range(3):
            task = Task(
                name=f"test-task-{i}",
                http_method="GET",
                endpoint_path=f"https://api.example.com/data{i}",
                dest_table="target_table",
                is_active=True,
            )
            db.add(task)
            db.commit()
            db.refresh(task)

            schedule = TaskSchedule(
                task_id=task.id,
                cron_expression="0 2 * * *",
                is_active=True,
                next_run_date=datetime.now(UTC),
                created_at=datetime.now(UTC),
            )
            db.add(schedule)
            db.commit()

        response = client.get("/api/v1/schedules/?skip=0&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 3
        assert len(data["schedules"]) == 2
        assert data["skip"] == 0
        assert data["limit"] == 2

    def test_list_schedules_filter_active(self, sample_task, db: Session):
        """Test filtering schedules by active status"""
        # Create active schedule
        active_schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=True,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(active_schedule)
        db.commit()

        # Create inactive task and schedule
        inactive_task = Task(
            name="test-task-inactive",
            http_method="GET",
            endpoint_path="https://api.example.com/data",
            dest_table="target_table",
            is_active=True,
        )
        db.add(inactive_task)
        db.commit()
        db.refresh(inactive_task)

        inactive_schedule = TaskSchedule(
            task_id=inactive_task.id,
            cron_expression="0 2 * * *",
            is_active=False,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(inactive_schedule)
        db.commit()

        # Get only active schedules
        response = client.get("/api/v1/schedules/?is_active=true")

        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] >= 1  # At least our active schedule
        for schedule in data["schedules"]:
            assert schedule["is_active"] is True


class TestResumeSchedule:
    """Test resuming paused schedules"""

    def test_resume_schedule(self, sample_task, db: Session):
        """Test resuming a paused schedule"""
        # Create inactive schedule
        schedule = TaskSchedule(
            task_id=sample_task.id,
            cron_expression="0 2 * * *",
            is_active=False,
            next_run_date=datetime.now(UTC),
            created_at=datetime.now(UTC),
        )
        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        response = client.post(f"/api/v1/schedules/{schedule.id}/resume")

        assert response.status_code == 200
        assert "resumed" in response.json()["message"].lower()

        # Verify schedule is active
        db.refresh(schedule)
        assert schedule.is_active is True

    def test_resume_schedule_not_found(self):
        """Test resuming non-existent schedule"""
        response = client.post("/api/v1/schedules/999999/resume")

        assert response.status_code == 404
