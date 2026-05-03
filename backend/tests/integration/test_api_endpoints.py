"""
Integration tests for API endpoints.

Tests the HTTP API workflows for task management, run triggering, and result retrieval.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.runs import get_db as runs_get_db
from app.api.v1.routes.tasks import get_db
from app.db.models.task import Task
from app.db.models.task_log import TaskLog
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.session import Base
from app.main import app

# ============================================================================
# Test Database Setup
# ============================================================================


@pytest.fixture(scope="function")
def test_db():
    """Create in-memory SQLite database for testing"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[runs_get_db] = override_get_db

    yield TestingSessionLocal()

    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture(autouse=True)
def mock_connection_dependencies(monkeypatch):
    storage = MagicMock()
    storage.get_connection.side_effect = lambda connection_id, include_password=False: (
        {"id": connection_id, "name": f"Connection {connection_id}"} if connection_id else None
    )
    monkeypatch.setattr("app.api.v1.routes.tasks.get_connection_storage", lambda: storage)
    monkeypatch.setattr(
        "app.api.v1.routes.tasks.enqueue_run", lambda task_id: MagicMock(id=f"task-{task_id}")
    )


@pytest.fixture
def client(test_db):
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def sample_task(test_db) -> Task:
    """Create a sample task"""
    task = Task(
        name="Test Import Task",
        description="Test data import",
        connection_id="conn-1",
        endpoint_path="/api/v1/test-data",
        dest_table="test_data",
        is_active=True,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
    return task


# ============================================================================
# Task CRUD Tests
# ============================================================================


def test_create_task(client: TestClient):
    """Test creating a new task"""
    response = client.post(
        "/api/v1/tasks/",
        json={
            "name": "New Task",
            "description": "Import user data",
            "connection_id": "conn-1",
            "endpoint_path": "/api/users",
            "dest_table": "users",
            "http_method": "GET",
            "batch_size": 1000,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "New Task"
    assert data["id"] is not None


def test_create_duplicate_task(client: TestClient, sample_task):
    """Test creating a task with duplicate name fails"""
    response = client.post(
        "/api/v1/tasks/",
        json={
            "name": sample_task.name,
            "connection_id": "conn-1",
            "endpoint_path": "/api/different",
            "dest_table": "different_table",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_list_tasks(client: TestClient, sample_task):
    """Test listing all tasks"""
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert any(t["id"] == sample_task.id for t in data)


def test_list_tasks_with_pagination(client: TestClient, test_db):
    """Test task list pagination"""
    # Create 3 tasks
    for i in range(3):
        task = Task(
            name=f"Task {i}",
            connection_id="conn-1",
            endpoint_path=f"/api/data{i}",
            dest_table=f"table{i}",
        )
        test_db.add(task)
    test_db.commit()

    # Test skip/limit
    response = client.get("/api/v1/tasks/?skip=0&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_tasks_with_filter(client: TestClient, test_db):
    """Test task list filtering by is_active"""
    # Create active and inactive tasks
    task1 = Task(
        name="Active",
        connection_id="conn-1",
        endpoint_path="/api/active",
        dest_table="t1",
        is_active=True,
    )
    task2 = Task(
        name="Inactive",
        connection_id="conn-1",
        endpoint_path="/api/inactive",
        dest_table="t2",
        is_active=False,
    )
    test_db.add_all([task1, task2])
    test_db.commit()

    # Filter active only
    response = client.get("/api/v1/tasks/?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert all(t["is_active"] for t in data)


def test_get_task(client: TestClient, sample_task):
    """Test getting a specific task"""
    response = client.get(f"/api/v1/tasks/{sample_task.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_task.id
    assert data["name"] == sample_task.name


def test_get_nonexistent_task(client: TestClient):
    """Test getting a nonexistent task"""
    response = client.get("/api/v1/tasks/99999")
    assert response.status_code == 404


def test_update_task(client: TestClient, sample_task):
    """Test updating a task"""
    response = client.put(
        f"/api/v1/tasks/{sample_task.id}",
        json={
            "name": "Updated Task",
            "description": "Updated description",
            "connection_id": "conn-2",
            "endpoint_path": "/api/updated",
            "dest_table": "updated_table",
            "is_active": False,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Task"
    assert not data["is_active"]


def test_delete_task(client: TestClient, sample_task):
    """Test deleting a task"""
    response = client.delete(f"/api/v1/tasks/{sample_task.id}")
    assert response.status_code == 204

    # Verify it's deleted
    response = client.get(f"/api/v1/tasks/{sample_task.id}")
    assert response.status_code == 404


# ============================================================================
# Task Run Tests
# ============================================================================


def test_trigger_task_run(client: TestClient, sample_task, test_db):
    """Test triggering a new task run"""
    response = client.post(f"/api/v1/tasks/{sample_task.id}/run")
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "enqueued"
    assert data["task_id"] == sample_task.id
    assert data["run_id"] is not None


def test_trigger_nonexistent_task_run(client: TestClient):
    """Test triggering a run for nonexistent task"""
    response = client.post("/api/v1/tasks/99999/run")
    assert response.status_code == 404


def test_list_task_runs(client: TestClient, sample_task, test_db):
    """Test listing runs for a task"""
    # Create some runs
    for i in range(3):
        run = TaskRun(
            task_id=sample_task.id,
            status=TaskStatus.SUCCESS.value if i % 2 == 0 else TaskStatus.FAILED.value,
            rows_fetched=100 + i,
            rows_inserted=100 + i,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        test_db.add(run)
    test_db.commit()

    response = client.get(f"/api/v1/tasks/{sample_task.id}/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3


def test_list_task_runs_with_status_filter(client: TestClient, sample_task, test_db):
    """Test filtering runs by status"""
    # Create runs with different statuses
    for status in [TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.PARTIAL_SUCCESS]:
        run = TaskRun(task_id=sample_task.id, status=status.value, started_at=datetime.now(UTC))
        test_db.add(run)
    test_db.commit()

    response = client.get(f"/api/v1/tasks/{sample_task.id}/runs?status={TaskStatus.SUCCESS.value}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["status"] == TaskStatus.SUCCESS.value


def test_get_task_run(client: TestClient, sample_task, test_db):
    """Test getting detailed task run information"""
    # Create a task run
    run = TaskRun(
        task_id=sample_task.id,
        status=TaskStatus.SUCCESS.value,
        rows_fetched=100,
        rows_inserted=100,
        error_count=0,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    test_db.add(run)
    test_db.commit()

    # Create a log entry
    log = TaskLog(
        task_run_id=run.id,
        step_name="FETCH_API",
        message="API fetch successful",
        details={"rows_fetched": 100},
    )
    test_db.add(log)
    test_db.commit()

    response = client.get(f"/api/v1/tasks/{sample_task.id}/runs/{run.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run.id
    assert data["status"] == TaskStatus.SUCCESS.value
    assert len(data["execution_logs"]) == 1


def test_get_nonexistent_run(client: TestClient, sample_task):
    """Test getting a nonexistent run"""
    response = client.get(f"/api/v1/tasks/{sample_task.id}/runs/99999")
    assert response.status_code == 404


# ============================================================================
# Task Stats Tests
# ============================================================================


def test_task_stats(client: TestClient, sample_task, test_db):
    """Test getting task statistics"""
    # Create runs
    runs_data = [
        (TaskStatus.SUCCESS, 100, 100, 0),
        (TaskStatus.SUCCESS, 200, 200, 0),
        (TaskStatus.PARTIAL_SUCCESS, 150, 140, 10),
    ]

    for status, fetched, inserted, failed in runs_data:
        run = TaskRun(
            task_id=sample_task.id,
            status=status.value,
            rows_fetched=fetched,
            rows_inserted=inserted,
            error_count=failed,
            started_at=datetime.now(UTC),
            ended_at=datetime.now(UTC),
        )
        test_db.add(run)
    test_db.commit()

    response = client.get(f"/api/v1/tasks/{sample_task.id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["task_id"] == sample_task.id
    assert data["total_runs"] == 3
    assert data["successful_runs"] == 2  # SUCCESS + PARTIAL_SUCCESS count as successful
    assert data["total_rows_fetched"] == 450
    assert data["total_rows_inserted"] == 440
    assert data["total_errors"] == 10
    assert data["success_rate"] >= 66.0  # 2 out of 3


def test_task_stats_no_runs(client: TestClient, sample_task):
    """Test task stats with no runs"""
    response = client.get(f"/api/v1/tasks/{sample_task.id}/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_runs"] == 0
    assert data["success_rate"] == 0.0
    assert data["avg_duration_seconds"] == 0.0


# ============================================================================
# Run Endpoint Tests
# ============================================================================


def test_get_run_by_id(client: TestClient, sample_task, test_db):
    """Test getting a run from the runs endpoint"""
    run = TaskRun(
        task_id=sample_task.id,
        status=TaskStatus.SUCCESS.value,
        rows_fetched=100,
        rows_inserted=100,
        started_at=datetime.now(UTC),
        ended_at=datetime.now(UTC),
    )
    test_db.add(run)
    test_db.commit()

    response = client.get(f"/api/v1/runs/{run.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == run.id
    assert data["task_id"] == sample_task.id


def test_list_all_runs(client: TestClient, test_db):
    """Test listing all runs across all tasks"""
    # Create 2 tasks with runs
    for t in range(2):
        task = Task(name=f"Task {t}", endpoint_path=f"/api/data{t}", dest_table=f"table{t}")
        test_db.add(task)
        test_db.flush()

        for r in range(2):
            run = TaskRun(
                task_id=task.id,
                status=TaskStatus.SUCCESS.value,
                started_at=datetime.now(UTC),
                ended_at=datetime.now(UTC),
            )
            test_db.add(run)
    test_db.commit()

    response = client.get("/api/v1/runs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 4  # 2 tasks * 2 runs


# ============================================================================
# Health Check Tests
# ============================================================================


def test_health_check(client: TestClient):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_root_endpoint(client: TestClient):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "docs" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
