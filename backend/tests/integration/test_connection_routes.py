"""
Integration tests for connection API routes.

Tests the full API endpoints with mocked database connections.
"""
import pytest
import os
import tempfile
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set test environment before importing app modules
os.environ["APP_ENV"] = "development"
os.environ["ENCRYPTION_KEY"] = "test_key_for_testing_purposes_only_32bytes!"


@pytest.fixture
def temp_connections_file():
    """Create a temporary file for connections storage"""
    fd, path = tempfile.mkstemp(suffix='.enc')
    os.close(fd)
    # Remove it so tests start fresh
    os.unlink(path)
    yield path
    # Cleanup
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def client(temp_connections_file):
    """Create test client with mocked connection storage path"""
    # Patch the default path before importing
    with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
        # Reset singleton
        import app.services.connection_storage as cs
        cs._storage_service = None

        from app.main import app
        with TestClient(app) as client:
            yield client


class TestConnectionRoutes:
    """Tests for connection API endpoints"""

    def test_list_connections_empty(self, client):
        """Test listing connections when none exist"""
        response = client.get("/api/v1/connections/")

        assert response.status_code == 200
        data = response.json()
        assert data["connections"] == []
        assert data["active_connection_id"] is None
        assert data["total_count"] == 0

    def test_create_connection_fails_without_valid_db(self, client):
        """Test that creating connection fails when DB is unreachable"""
        response = client.post("/api/v1/connections/", json={
            "name": "Test DB",
            "db_type": "oracle",
            "host": "nonexistent.invalid.host",
            "port": 1521,
            "username": "testuser",
            "password": "testpass",
            "service_name": "ORCL",
        })

        # Should fail because connection test fails
        assert response.status_code == 400
        assert "Connection test failed" in response.json()["detail"]

    def test_test_connection_endpoint(self, client):
        """Test the connection test endpoint"""
        response = client.post("/api/v1/connections/test", json={
            "db_type": "oracle",
            "host": "nonexistent.invalid.host",
            "port": 1521,
            "username": "testuser",
            "password": "testpass",
            "service_name": "ORCL",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == False
        assert "message" in data

    def test_get_connection_not_found(self, client):
        """Test getting non-existent connection returns 404"""
        response = client.get("/api/v1/connections/non-existent-id")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_connection_not_found(self, client):
        """Test updating non-existent connection returns 404"""
        response = client.put("/api/v1/connections/non-existent-id", json={
            "name": "New Name",
        })

        assert response.status_code == 404

    def test_delete_connection_not_found(self, client):
        """Test deleting non-existent connection returns 404"""
        response = client.delete("/api/v1/connections/non-existent-id")

        assert response.status_code == 404

    def test_activate_connection_not_found(self, client):
        """Test activating non-existent connection returns 404"""
        response = client.post("/api/v1/connections/non-existent-id/activate")

        assert response.status_code == 404


class TestConnectionRoutesWithMockedDB:
    """Tests with mocked successful database connection"""

    @pytest.fixture
    def mock_test_connection(self):
        """Mock the test_connection function to always succeed"""
        with patch('app.api.v1.routes.connections.test_connection') as mock:
            mock.return_value = {
                "success": True,
                "message": "Connection successful",
                "latency_ms": 50,
                "server_version": "Oracle 19c",
            }
            yield mock

    def test_create_connection_success(self, client, mock_test_connection, temp_connections_file):
        """Test successfully creating a connection"""
        # Reset the singleton to use the temp file
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            response = client.post("/api/v1/connections/", json={
                "name": "Test DB",
                "db_type": "oracle",
                "host": "localhost",
                "port": 1521,
                "username": "testuser",
                "password": "testpass",
                "service_name": "ORCL",
            })

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "Test DB"
            assert data["host"] == "localhost"
            assert data["db_type"] == "oracle"
            assert "id" in data
            assert data["is_default"] == True
            # Password should NOT be in response
            assert "password" not in data or data.get("password") != "testpass"

    def test_create_and_list_connections(self, client, mock_test_connection, temp_connections_file):
        """Test creating multiple connections and listing them"""
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            # Create first connection
            resp1 = client.post("/api/v1/connections/", json={
                "name": "DB 1",
                "host": "host1",
                "username": "user1",
                "password": "pass1",
                "service_name": "ORCL1",
            })
            assert resp1.status_code == 201

            # Create second connection
            resp2 = client.post("/api/v1/connections/", json={
                "name": "DB 2",
                "host": "host2",
                "username": "user2",
                "password": "pass2",
                "service_name": "ORCL2",
            })
            assert resp2.status_code == 201

            # List connections
            list_resp = client.get("/api/v1/connections/")
            assert list_resp.status_code == 200
            data = list_resp.json()
            assert data["total_count"] == 2
            assert len(data["connections"]) == 2

            # First connection should be active
            assert data["active_connection_id"] == resp1.json()["id"]

    def test_update_connection(self, client, mock_test_connection, temp_connections_file):
        """Test updating a connection"""
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            # Create connection
            create_resp = client.post("/api/v1/connections/", json={
                "name": "Original Name",
                "host": "localhost",
                "username": "user",
                "password": "pass",
                "service_name": "ORCL",
            })
            conn_id = create_resp.json()["id"]

            # Update connection
            update_resp = client.put(f"/api/v1/connections/{conn_id}", json={
                "name": "Updated Name",
            })

            assert update_resp.status_code == 200
            assert update_resp.json()["name"] == "Updated Name"

    def test_delete_connection(self, client, mock_test_connection, temp_connections_file):
        """Test deleting a connection"""
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            # Create connection
            create_resp = client.post("/api/v1/connections/", json={
                "name": "To Delete",
                "host": "localhost",
                "username": "user",
                "password": "pass",
                "service_name": "ORCL",
            })
            conn_id = create_resp.json()["id"]

            # Delete connection
            delete_resp = client.delete(f"/api/v1/connections/{conn_id}")
            assert delete_resp.status_code == 204

            # Verify deleted
            get_resp = client.get(f"/api/v1/connections/{conn_id}")
            assert get_resp.status_code == 404

    def test_activate_connection(self, client, mock_test_connection, temp_connections_file):
        """Test activating a different connection"""
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            # Create two connections
            resp1 = client.post("/api/v1/connections/", json={
                "name": "DB 1",
                "host": "host1",
                "username": "user1",
                "password": "pass1",
                "service_name": "ORCL1",
            })
            conn1_id = resp1.json()["id"]

            resp2 = client.post("/api/v1/connections/", json={
                "name": "DB 2",
                "host": "host2",
                "username": "user2",
                "password": "pass2",
                "service_name": "ORCL2",
            })
            conn2_id = resp2.json()["id"]

            # First should be active
            list_resp = client.get("/api/v1/connections/")
            assert list_resp.json()["active_connection_id"] == conn1_id

            # Activate second
            activate_resp = client.post(f"/api/v1/connections/{conn2_id}/activate")
            assert activate_resp.status_code == 200

            # Second should now be active
            list_resp = client.get("/api/v1/connections/")
            assert list_resp.json()["active_connection_id"] == conn2_id

    def test_get_single_connection(self, client, mock_test_connection, temp_connections_file):
        """Test getting a single connection by ID"""
        with patch.dict(os.environ, {"CONNECTIONS_FILE_PATH": temp_connections_file}):
            import app.services.connection_storage as cs
            cs._storage_service = None

            # Create connection
            create_resp = client.post("/api/v1/connections/", json={
                "name": "Test DB",
                "host": "localhost",
                "port": 5432,
                "db_type": "postgresql",
                "username": "admin",
                "password": "secret",
                "database": "mydb",
            })
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
        response = client.post("/api/v1/connections/", json={
            "name": "Test",
            # Missing host, username, password
        })

        assert response.status_code == 422

    def test_create_connection_invalid_port(self, client):
        """Test that invalid port returns 422"""
        response = client.post("/api/v1/connections/", json={
            "name": "Test",
            "host": "localhost",
            "port": 99999,  # Invalid port
            "username": "user",
            "password": "pass",
            "service_name": "ORCL",
        })

        assert response.status_code == 422

    def test_create_connection_invalid_db_type(self, client):
        """Test that invalid db_type returns 422"""
        response = client.post("/api/v1/connections/", json={
            "name": "Test",
            "host": "localhost",
            "db_type": "mongodb",  # Not supported
            "username": "user",
            "password": "pass",
        })

        assert response.status_code == 422
