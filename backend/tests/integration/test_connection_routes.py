"""
Integration tests for connection API routes.

Tests the full API endpoints with mocked database connections.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

# Set test environment before importing app modules
os.environ["APP_ENV"] = "development"
os.environ["ENCRYPTION_KEY"] = "ancg5kTQFZYtqA3LyzV9MrixQ1HyC95gitaGyZ1nDPk="


@pytest.fixture(scope="function")
def temp_connections_file():
    """Create a temporary file for connections storage"""
    fd, path = tempfile.mkstemp(suffix=".enc")
    os.close(fd)
    # Remove it so tests start fresh
    os.unlink(path)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture(scope="function")
def client(temp_connections_file):
    """Create test client with mocked connection storage path"""
    # Set environment before app creation
    os.environ["CONNECTIONS_FILE_PATH"] = temp_connections_file

    # Reset singleton before test
    import app.services.connection_storage as cs

    cs._storage_service = None

    from app.main import app

    test_client = TestClient(app)
    yield test_client
    test_client.close()

    # Reset after test
    cs._storage_service = None


class TestConnectionRoutes:
    """Tests for connection API endpoints"""

    @pytest.fixture(autouse=True, scope="function")
    def cleanup_connections_file(self):
        """Clean up the connections file before each test"""
        # Delete the real connections file if it exists
        from app.services.connection_storage import ConnectionStorageService

        service = ConnectionStorageService()
        if service.file_path.exists():
            service.file_path.unlink()

        yield

        # Cleanup after test
        if service.file_path.exists():
            service.file_path.unlink()

    def test_list_connections_empty(self, client):
        """Test listing connections when none exist"""
        response = client.get("/api/v1/connections/")

        assert response.status_code == 200
        data = response.json()
        assert data["connections"] == []
        assert data["total_count"] == 0

    def test_create_connection_fails_without_valid_db(self, client):
        """Test that creating connection fails when DB is unreachable"""
        response = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test DB",
                "db_type": "oracle",
                "host": "nonexistent.invalid.host",
                "port": 1521,
                "username": "testuser",
                "password": "testpass",
                "service_name": "ORCL",
            },
        )

        # Should fail because connection test fails
        assert response.status_code == 400
        assert "Connection test failed" in response.json()["detail"]

    def test_test_connection_endpoint(self, client):
        """Test the connection test endpoint"""
        response = client.post(
            "/api/v1/connections/test",
            json={
                "db_type": "oracle",
                "host": "nonexistent.invalid.host",
                "port": 1521,
                "username": "testuser",
                "password": "testpass",
                "service_name": "ORCL",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert not data["success"]
        assert "message" in data

    def test_get_connection_not_found(self, client):
        """Test getting non-existent connection returns 404"""
        response = client.get("/api/v1/connections/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_connection_not_found(self, client):
        """Test updating non-existent connection returns 404"""
        response = client.put(
            "/api/v1/connections/non-existent-id",
            json={
                "name": "New Name",
            },
        )

        assert response.status_code == 404

    def test_delete_connection_not_found(self, client):
        """Test deleting non-existent connection returns 404"""
        response = client.delete("/api/v1/connections/non-existent-id")

        assert response.status_code == 404


class TestConnectionRoutesWithMockedDB:
    """Tests with mocked successful database connection"""

    @pytest.fixture
    def mock_test_connection(self):
        """Mock the test_connection function to always succeed"""
        with patch("app.api.v1.routes.connections.test_connection") as mock:
            mock.return_value = {
                "success": True,
                "message": "Connection successful",
                "latency_ms": 50,
                "server_version": "Oracle 19c",
            }
            yield mock

    def test_create_connection_success(self, client, mock_test_connection, temp_connections_file):
        """Test successfully creating a connection"""
        response = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test DB",
                "db_type": "oracle",
                "host": "localhost",
                "port": 1521,
                "username": "testuser",
                "password": "testpass",
                "service_name": "ORCL",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test DB"
        assert data["host"] == "localhost"
        assert data["db_type"] == "oracle"
        assert "id" in data
        assert "is_default" not in data
        # Password should NOT be in response
        assert "password" not in data or data.get("password") != "testpass"

        # Clean up for next tests
        conn_id = data["id"]
        delete_resp = client.delete(f"/api/v1/connections/{conn_id}")
        assert delete_resp.status_code == 204

    def test_create_and_list_connections(self, client, mock_test_connection, temp_connections_file):
        """Test creating multiple connections and listing them"""
        # Create first connection
        resp1 = client.post(
            "/api/v1/connections/",
            json={
                "name": "DB 1",
                "host": "host1",
                "username": "user1",
                "password": "pass1",
                "service_name": "ORCL1",
            },
        )
        assert resp1.status_code == 201

        # Create second connection
        resp2 = client.post(
            "/api/v1/connections/",
            json={
                "name": "DB 2",
                "host": "host2",
                "username": "user2",
                "password": "pass2",
                "service_name": "ORCL2",
            },
        )
        assert resp2.status_code == 201

        # List connections
        list_resp = client.get("/api/v1/connections/")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total_count"] == 2
        assert len(data["connections"]) == 2

    def test_update_connection(self, client, mock_test_connection, temp_connections_file):
        """Test updating a connection"""
        # Create connection
        create_resp = client.post(
            "/api/v1/connections/",
            json={
                "name": "Original Name",
                "host": "localhost",
                "username": "user",
                "password": "pass",
                "service_name": "ORCL",
            },
        )
        conn_id = create_resp.json()["id"]

        # Update connection
        update_resp = client.put(
            f"/api/v1/connections/{conn_id}",
            json={
                "name": "Updated Name",
            },
        )

        assert update_resp.status_code == 200
        assert update_resp.json()["name"] == "Updated Name"

    def test_delete_connection(self, client, mock_test_connection, temp_connections_file):
        """Test deleting a connection"""
        # Create connection
        create_resp = client.post(
            "/api/v1/connections/",
            json={
                "name": "To Delete",
                "host": "localhost",
                "username": "user",
                "password": "pass",
                "service_name": "ORCL",
            },
        )
        conn_id = create_resp.json()["id"]

        # Delete connection
        delete_resp = client.delete(f"/api/v1/connections/{conn_id}")
        assert delete_resp.status_code == 204

        # Verify deleted
        get_resp = client.get(f"/api/v1/connections/{conn_id}")
        assert get_resp.status_code == 404

    def test_get_single_connection(self, client, mock_test_connection, temp_connections_file):
        """Test getting a single connection by ID"""
        # Create connection
        create_resp = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test DB",
                "host": "localhost",
                "port": 5432,
                "db_type": "postgresql",
                "username": "admin",
                "password": "secret",
                "database": "mydb",
            },
        )
        conn_id = create_resp.json()["id"]

        # Get connection
        get_resp = client.get(f"/api/v1/connections/{conn_id}")

        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["id"] == conn_id
        assert data["name"] == "Test DB"
        assert data["db_type"] == "postgresql"
        assert data["database"] == "mydb"


class TestConnectionValidation:
    """Tests for input validation"""

    def test_create_connection_missing_required_fields(self, client):
        """Test that missing required fields return 422"""
        response = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test",
                # Missing host, username, password
            },
        )

        assert response.status_code == 422

    def test_create_connection_invalid_port(self, client):
        """Test that invalid port returns 422"""
        response = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test",
                "host": "localhost",
                "port": 99999,  # Invalid port
                "username": "user",
                "password": "pass",
                "service_name": "ORCL",
            },
        )

        assert response.status_code == 422

    def test_create_connection_invalid_db_type(self, client):
        """Test that invalid db_type returns 422"""
        response = client.post(
            "/api/v1/connections/",
            json={
                "name": "Test",
                "host": "localhost",
                "db_type": "mongodb",  # Not supported
                "username": "user",
                "password": "pass",
            },
        )

        assert response.status_code == 422
