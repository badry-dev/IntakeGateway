"""Tests for bounded read endpoints and config-time identifier validation
(v1.4 phase 3, tasks 17 & 19)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.runs import get_db as runs_get_db
from app.api.v1.routes.tasks import get_db
from app.db.models.task import Task
from app.db.models.task_run import TaskRun
from app.db.session import Base
from app.main import app


@pytest.fixture(scope="function")
def test_db():
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


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture(autouse=True)
def mock_connection_dependencies(monkeypatch):
    from unittest.mock import MagicMock

    storage = MagicMock()
    storage.get_connection.side_effect = lambda connection_id, include_password=False: (
        {"id": connection_id, "name": f"Connection {connection_id}"} if connection_id else None
    )
    monkeypatch.setattr("app.api.v1.routes.tasks.get_connection_storage", lambda: storage)


@pytest.fixture
def task_with_runs(test_db):
    from datetime import UTC, datetime, timedelta

    task = Task(
        name="Stats Task",
        connection_id="conn-1",
        endpoint_path="/api/x",
        dest_table="x",
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    base = datetime.now(UTC)
    statuses = ["SUCCESS", "SUCCESS", "FAILED", "PARTIAL_SUCCESS"]
    for i, status in enumerate(statuses):
        run = TaskRun(
            task_id=task.id,
            status=status,
            started_at=base - timedelta(minutes=len(statuses) - i),
            ended_at=base - timedelta(minutes=len(statuses) - i - 1),
            rows_fetched=100,
            rows_inserted=80,
            rows_updated=10,
            rows_skipped=5,
            error_count=2,
        )
        test_db.add(run)
    test_db.commit()
    return task


class TestStatsAggregation:
    def test_stats_correct_and_aggregated(self, client, task_with_runs):
        resp = client.get(f"/api/v1/tasks/{task_with_runs.id}/stats")
        assert resp.status_code == 200
        data = resp.json()

        assert data["total_runs"] == 4
        assert data["successful_runs"] == 2
        assert data["failed_runs"] == 1
        assert data["success_rate"] == 50.0
        assert data["total_rows_fetched"] == 400
        assert data["total_rows_inserted"] == 320
        assert data["total_errors"] == 8
        assert data["avg_duration_seconds"] > 0
        assert data["last_run_status"] is not None


class TestIdentifierValidation:
    def test_dest_table_rejects_injection(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "bad table",
                "connection_id": "conn-1",
                "endpoint_path": "https://api.example.com/x",
                "dest_table": 'evil"; DROP TABLE tasks; --',
            },
        )
        assert resp.status_code == 422

    def test_dest_table_allows_schema_qualified(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "qualified",
                "connection_id": "conn-1",
                "endpoint_path": "https://api.example.com/x",
                "dest_table": "SCHEMA.TABLE_NAME",
            },
        )
        assert resp.status_code == 201, resp.text

    def test_upsert_keys_entries_validated(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "bad keys",
                "connection_id": "conn-1",
                "endpoint_path": "https://api.example.com/x",
                "dest_table": "TBL",
                "upsert_enabled": True,
                "upsert_keys": ['ok_key", "injected'],
            },
        )
        assert resp.status_code == 422

    def test_skip_column_validated(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "bad skip",
                "connection_id": "conn-1",
                "endpoint_path": "https://api.example.com/x",
                "dest_table": "TBL",
                "skip_column": 'a"; DROP TABLE x',
            },
        )
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
