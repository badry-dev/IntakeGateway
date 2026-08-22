"""Tests for PUT /tasks/{id} partial update semantics (v1.4 H3)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.routes.runs import get_db as runs_get_db
from app.api.v1.routes.tasks import get_db
from app.core.encryption import decrypt_value
from app.db.models.task import Task
from app.db.session import Base
from app.main import app


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
    storage = MagicMock = None  # noqa: F841 - placeholder to keep flake quiet
    from unittest.mock import MagicMock as _M

    storage = _M()
    storage.get_connection.side_effect = lambda connection_id, include_password=False: (
        {"id": connection_id, "name": f"Connection {connection_id}"} if connection_id else None
    )
    monkeypatch.setattr("app.api.v1.routes.tasks.get_connection_storage", lambda: storage)


@pytest.fixture
def client(test_db):
    return TestClient(app)


@pytest.fixture
def bearer_task(test_db) -> Task:
    task = Task(
        name="Bearer Task",
        connection_id="conn-1",
        endpoint_path="/api/users",
        dest_table="users",
        auth_type="bearer",
        api_key="ENCRYPTED_BLOB",
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)
    return task


def _create_task(client: TestClient, name: str) -> dict:
    resp = client.post(
        "/api/v1/tasks/",
        json={
            "name": name,
            "connection_id": "conn-1",
            "endpoint_path": "https://api.example.com/users",
            "dest_table": "users",
            "auth_type": "bearer",
            "api_key": "plaintext-secret-123",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestPartialUpdate:
    def test_update_name_only_preserves_api_key(self, client, test_db):
        """Updating an unrelated field must not wipe stored credentials."""
        created = _create_task(client, "Keep Secret")
        task_id = created["id"]

        resp = client.put(f"/api/v1/tasks/{task_id}", json={"name": "Renamed"})
        assert resp.status_code == 200, resp.text

        row = test_db.query(Task).filter(Task.id == task_id).first()
        assert row.name == "Renamed"
        assert row.api_key is not None
        assert row.api_key != "plaintext-secret-123"
        assert decrypt_value(row.api_key) == "plaintext-secret-123"

    def test_empty_string_secret_explicitly_clears(self, client, test_db):
        created = _create_task(client, "Clear Secret")
        task_id = created["id"]

        resp = client.put(f"/api/v1/tasks/{task_id}", json={"api_key": ""})
        assert resp.status_code == 200

        row = test_db.query(Task).filter(Task.id == task_id).first()
        assert row.api_key is None

    def test_auth_type_change_without_secret_is_422(self, client):
        created = _create_task(client, "No Secret Switch")
        task_id = created["id"]

        resp = client.put(f"/api/v1/tasks/{task_id}", json={"auth_type": "bearer", "name": "x"})
        assert resp.status_code == 422

    def test_unset_defaults_not_reset(self, client, test_db):
        """upsert_enabled etc. must not silently reset to defaults."""
        created = _create_task(client, "Defaults Kept")
        task_id = created["id"]
        test_db.query(Task).filter(Task.id == task_id).update(
            {"upsert_enabled": True, "batch_size": 250}
        )
        test_db.commit()

        resp = client.put(f"/api/v1/tasks/{task_id}", json={"description": "updated"})
        assert resp.status_code == 200

        row = test_db.query(Task).filter(Task.id == task_id).first()
        assert row.upsert_enabled is True
        assert row.batch_size == 250

    def test_endpoint_path_ssrf_rejected(self, client):
        created = _create_task(client, "SSRF Update")
        task_id = created["id"]

        resp = client.put(
            f"/api/v1/tasks/{task_id}",
            json={"endpoint_path": "http://169.254.169.254/latest/meta-data/"},
        )
        assert resp.status_code == 422


class TestTaskCreateSSRFValidation:
    def test_create_rejects_metadata_url(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "SSRF Create",
                "connection_id": "conn-1",
                "endpoint_path": "http://127.0.0.1:6379/",
                "dest_table": "t",
            },
        )
        assert resp.status_code == 422

    def test_create_rejects_non_http_scheme(self, client):
        resp = client.post(
            "/api/v1/tasks/",
            json={
                "name": "File Scheme",
                "connection_id": "conn-1",
                "endpoint_path": "file:///etc/passwd",
                "dest_table": "t",
            },
        )
        assert resp.status_code == 422


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
