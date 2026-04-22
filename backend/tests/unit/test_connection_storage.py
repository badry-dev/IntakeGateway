"""
Unit tests for connection storage service.

Tests encryption, CRUD operations, and file handling.
"""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set test environment before importing app modules
os.environ["APP_ENV"] = "development"
os.environ["ENCRYPTION_KEY"] = "ancg5kTQFZYtqA3LyzV9MrixQ1HyC95gitaGyZ1nDPk="


class TestConnectionStorage:
    """Tests for ConnectionStorageService"""

    @pytest.fixture
    def temp_file(self):
        """Create a temporary file for testing"""
        fd, path = tempfile.mkstemp(suffix='.enc')
        os.close(fd)
        yield path
        # Cleanup
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def storage_service(self, temp_file):
        """Create a storage service with temp file"""
        from app.services.connection_storage import ConnectionStorageService
        return ConnectionStorageService(file_path=temp_file)

    def test_empty_file_returns_empty_list(self, temp_file):
        """Test that non-existent file returns empty structure"""
        # Remove the temp file to simulate non-existent
        os.unlink(temp_file)

        from app.services.connection_storage import ConnectionStorageService
        service = ConnectionStorageService(file_path=temp_file)

        result = service.list_connections()

        assert result["connections"] == []
        assert result["version"] == 1
        assert "active_connection_id" not in result

    def test_create_connection_encrypts_password(self, storage_service):
        """Test that password is encrypted when creating connection"""
        connection_data = {
            "name": "Test DB",
            "db_type": "oracle",
            "host": "localhost",
            "port": 1521,
            "username": "testuser",
            "password": "secretpassword",
            "service_name": "ORCL",
        }

        result = storage_service.create_connection(connection_data)

        # Password should be masked in response
        assert result["password"] == "********"
        assert result["name"] == "Test DB"
        assert result["id"] is not None
        assert "is_default" not in result

    def test_corrupted_file_returns_empty_structure(self, temp_file):
        """Unreadable encrypted data should not break the app."""
        Path(temp_file).write_text("not-valid-encrypted-data", encoding="utf-8")

        from app.services.connection_storage import ConnectionStorageService
        service = ConnectionStorageService(file_path=temp_file)

        result = service.list_connections()

        assert result["connections"] == []
        assert result["version"] == 1
        assert "active_connection_id" not in result

    def test_create_multiple_connections(self, storage_service):
        """Test creating multiple connections"""
        conn1 = storage_service.create_connection({
            "name": "DB 1",
            "host": "host1",
            "username": "user1",
            "password": "pass1",
            "service_name": "ORCL1",
        })

        conn2 = storage_service.create_connection({
            "name": "DB 2",
            "host": "host2",
            "username": "user2",
            "password": "pass2",
            "service_name": "ORCL2",
        })

        assert "is_default" not in conn1
        assert "is_default" not in conn2

        # List should have both
        result = storage_service.list_connections()
        assert len(result["connections"]) == 2
        assert "active_connection_id" not in result

    def test_list_connections_masks_passwords(self, storage_service):
        """Test that list_connections masks all passwords"""
        storage_service.create_connection({
            "name": "Test DB",
            "host": "localhost",
            "username": "user",
            "password": "verysecret",
            "service_name": "ORCL",
        })

        result = storage_service.list_connections()

        for conn in result["connections"]:
            assert conn["password"] == "********"

    def test_get_connection_by_id(self, storage_service):
        """Test retrieving a specific connection"""
        created = storage_service.create_connection({
            "name": "Test DB",
            "host": "localhost",
            "username": "user",
            "password": "secret",
            "service_name": "ORCL",
        })

        result = storage_service.get_connection(created["id"])

        assert result is not None
        assert result["name"] == "Test DB"
        assert result["password"] == "********"

    def test_get_connection_not_found(self, storage_service):
        """Test getting non-existent connection returns None"""
        result = storage_service.get_connection("non-existent-id")
        assert result is None

    def test_update_connection_without_password(self, storage_service):
        """Test updating connection preserves password when not provided"""
        created = storage_service.create_connection({
            "name": "Original Name",
            "host": "localhost",
            "username": "user",
            "password": "original_password",
            "service_name": "ORCL",
        })

        # Update without password
        updated = storage_service.update_connection(created["id"], {
            "name": "New Name",
        })

        assert updated["name"] == "New Name"

        # Verify password still works by decrypting
        decrypted = storage_service.get_decrypted_password(created["id"])
        assert decrypted == "original_password"

    def test_update_connection_with_new_password(self, storage_service):
        """Test updating connection with new password"""
        created = storage_service.create_connection({
            "name": "Test DB",
            "host": "localhost",
            "username": "user",
            "password": "old_password",
            "service_name": "ORCL",
        })

        storage_service.update_connection(created["id"], {
            "password": "new_password",
        })

        # Verify new password
        decrypted = storage_service.get_decrypted_password(created["id"])
        assert decrypted == "new_password"

    def test_delete_connection(self, storage_service):
        """Test deleting a connection"""
        created = storage_service.create_connection({
            "name": "Test DB",
            "host": "localhost",
            "username": "user",
            "password": "secret",
            "service_name": "ORCL",
        })

        result = storage_service.delete_connection(created["id"])

        assert result == True
        assert storage_service.get_connection(created["id"]) is None

    def test_delete_connection_not_found(self, storage_service):
        """Test deleting non-existent connection returns False"""
        result = storage_service.delete_connection("non-existent-id")
        assert result == False

    def test_delete_one_connection_keeps_the_rest(self, storage_service):
        """Deleting one connection should keep the others intact."""
        conn1 = storage_service.create_connection({
            "name": "DB 1",
            "host": "host1",
            "username": "user1",
            "password": "pass1",
            "service_name": "ORCL1",
        })

        conn2 = storage_service.create_connection({
            "name": "DB 2",
            "host": "host2",
            "username": "user2",
            "password": "pass2",
            "service_name": "ORCL2",
        })

        storage_service.delete_connection(conn1["id"])

        result = storage_service.list_connections()
        assert len(result["connections"]) == 1
        assert result["connections"][0]["id"] == conn2["id"]
        assert "active_connection_id" not in result

    def test_get_decrypted_password(self, storage_service):
        """Test decrypting password for internal use"""
        storage_service.create_connection({
            "name": "Test DB",
            "host": "localhost",
            "username": "user",
            "password": "supersecret123",
            "service_name": "ORCL",
        })

        connections = storage_service.list_connections()
        conn_id = connections["connections"][0]["id"]

        decrypted = storage_service.get_decrypted_password(conn_id)

        assert decrypted == "supersecret123"

    def test_encryption_roundtrip(self, storage_service):
        """Test that data survives encryption roundtrip"""
        original_data = {
            "name": "Test with Special Chars: éàü!@#$%",
            "host": "db.example.com",
            "port": 5432,
            "username": "admin",
            "password": "P@ssw0rd!#$%^&*()",
            "service_name": "PROD",
        }

        created = storage_service.create_connection(original_data)
        retrieved = storage_service.get_connection(created["id"])

        assert retrieved["name"] == original_data["name"]
        assert retrieved["host"] == original_data["host"]
        assert retrieved["port"] == original_data["port"]
        assert retrieved["username"] == original_data["username"]

        # Password should decrypt correctly
        decrypted = storage_service.get_decrypted_password(created["id"])
        assert decrypted == original_data["password"]


class TestConnectionPool:
    """Tests for connection pool manager"""

    def test_build_oracle_url(self):
        """Test building Oracle connection URL"""
        from app.services.connection_pool import build_connection_url

        conn = {
            "db_type": "oracle",
            "host": "localhost",
            "port": 1521,
            "username": "admin",
            "service_name": "ORCL",
        }

        url = build_connection_url(conn, "password123")

        assert "oracle+oracledb://" in url
        assert "admin:password123" in url
        assert "localhost:1521" in url
        assert "service_name=ORCL" in url

    def test_build_postgresql_url(self):
        """Test building PostgreSQL connection URL"""
        from app.services.connection_pool import build_connection_url

        conn = {
            "db_type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "username": "admin",
            "database": "mydb",
        }

        url = build_connection_url(conn, "password123")

        assert "postgresql+psycopg2://" in url
        assert "admin:password123" in url
        assert "localhost:5432" in url
        assert "/mydb" in url

    def test_build_mysql_url(self):
        """Test building MySQL connection URL"""
        from app.services.connection_pool import build_connection_url

        conn = {
            "db_type": "mysql",
            "host": "localhost",
            "port": 3306,
            "username": "admin",
            "database": "mydb",
        }

        url = build_connection_url(conn, "password123")

        assert "mysql+pymysql://" in url
        assert "admin:password123" in url
        assert "localhost:3306" in url
        assert "/mydb" in url

    def test_build_url_with_special_chars_password(self):
        """Test URL encoding of special characters in password"""
        from app.services.connection_pool import build_connection_url

        conn = {
            "db_type": "oracle",
            "host": "localhost",
            "port": 1521,
            "username": "admin",
            "service_name": "ORCL",
        }

        # Password with special chars that need URL encoding
        url = build_connection_url(conn, "pass@word/with?special=chars")

        # Special chars should be URL encoded
        assert "@" not in url.split("@")[0].split(":")[-1]  # @ in password should be encoded
        assert "%40" in url or "%2F" in url or "%3F" in url  # Some encoding present

    def test_unsupported_db_type_raises(self):
        """Test that unsupported DB type raises ValueError"""
        from app.services.connection_pool import build_connection_url

        conn = {
            "db_type": "mongodb",
            "host": "localhost",
            "port": 27017,
            "username": "admin",
        }

        with pytest.raises(ValueError, match="Unsupported database type"):
            build_connection_url(conn, "password")


class TestConnectionTestFunction:
    """Tests for test_connection function"""

    def test_test_connection_failure_returns_dict(self):
        """Test that failed connection test returns proper dict"""
        from app.services.connection_pool import test_connection

        # Use invalid connection that will fail
        result = test_connection({
            "db_type": "oracle",
            "host": "nonexistent.invalid.host",
            "port": 1521,
            "username": "user",
            "password": "pass",
            "service_name": "ORCL",
        })

        assert result["success"] == False
        assert "message" in result
        assert result["latency_ms"] is None
        assert result["server_version"] is None
