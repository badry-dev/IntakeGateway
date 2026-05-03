"""
Connection File Service - Encrypted file storage for database connections.

Uses Fernet symmetric encryption to securely store Oracle connection credentials
in a JSON file. The encryption key is derived from the application's SECRET_KEY.
"""

import json
import os
from pathlib import Path
from typing import Optional
from datetime import datetime
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.core.config import settings


class ConnectionFileService:
    """Service for managing encrypted database connection configurations."""

    # Connection file location (in app data directory)
    DEFAULT_CONNECTION_FILE = Path(__file__).parent.parent.parent / "data" / "connections.enc"

    def __init__(self, connection_file: Optional[Path] = None):
        """
        Initialize the connection service.

        Args:
            connection_file: Optional custom path for the encrypted connections file.
                           Defaults to backend/data/connections.enc
        """
        self.connection_file = connection_file or self.DEFAULT_CONNECTION_FILE
        self._ensure_data_directory()
        self._fernet = self._create_fernet()

    def _ensure_data_directory(self) -> None:
        """Create the data directory if it doesn't exist."""
        self.connection_file.parent.mkdir(parents=True, exist_ok=True)

    def _create_fernet(self) -> Fernet:
        """
        Create a Fernet instance using the application's SECRET_KEY.

        Uses PBKDF2 to derive a proper encryption key from the SECRET_KEY.
        """
        # Use a fixed salt (stored with the app) - in production, consider per-file salt
        salt = b"api2db_connection_salt_v1"

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=480000,  # OWASP recommended minimum for PBKDF2-SHA256
        )

        key = base64.urlsafe_b64encode(kdf.derive(settings.SECRET_KEY.encode()))
        return Fernet(key)

    def _read_connections(self) -> dict:
        """
        Read and decrypt connections from file.

        Returns:
            Dictionary of connections, empty dict if file doesn't exist.
        """
        if not self.connection_file.exists():
            return {"connections": [], "updated_at": None}

        try:
            encrypted_data = self.connection_file.read_bytes()
            decrypted_data = self._fernet.decrypt(encrypted_data)
            return json.loads(decrypted_data.decode("utf-8"))
        except Exception as e:
            # If decryption fails (wrong key, corrupted file), start fresh
            # Log this in production
            print(f"Warning: Could not read connections file: {e}")
            return {"connections": [], "updated_at": None}

    def _write_connections(self, data: dict) -> None:
        """
        Encrypt and write connections to file.

        Args:
            data: Dictionary containing connections list and metadata.
        """
        data["updated_at"] = datetime.utcnow().isoformat()
        json_data = json.dumps(data, indent=2)
        encrypted_data = self._fernet.encrypt(json_data.encode("utf-8"))
        self.connection_file.write_bytes(encrypted_data)

    def get_connection(self, name: str = "default") -> Optional[dict]:
        """
        Get a specific connection by name.

        Args:
            name: Connection name (default: "default")

        Returns:
            Connection dictionary or None if not found.
        """
        data = self._read_connections()
        for conn in data.get("connections", []):
            if conn.get("name") == name:
                return conn
        return None

    def get_all_connections(self) -> list[dict]:
        """
        Get all stored connections.

        Returns:
            List of connection dictionaries.
        """
        data = self._read_connections()
        return data.get("connections", [])

    def get_active_connection(self) -> Optional[dict]:
        """
        Get the currently active connection.

        Returns:
            Active connection dictionary or None if no active connection.
        """
        data = self._read_connections()
        for conn in data.get("connections", []):
            if conn.get("is_active", False):
                return conn
        # If no active connection, return the first one or None
        connections = data.get("connections", [])
        return connections[0] if connections else None

    def create_connection(
        self,
        name: str,
        host: str,
        port: int,
        service_name: str,
        username: str,
        password: str,
        is_active: bool = False,
        description: Optional[str] = None,
    ) -> dict:
        """
        Create a new connection configuration.

        Args:
            name: Unique connection name
            host: Oracle host
            port: Oracle port
            service_name: Oracle service name
            username: Database username
            password: Database password
            is_active: Whether this is the active connection
            description: Optional description

        Returns:
            Created connection dictionary.

        Raises:
            ValueError: If connection with same name already exists.
        """
        data = self._read_connections()

        # Check for duplicate name
        for conn in data.get("connections", []):
            if conn.get("name") == name:
                raise ValueError(f"Connection with name '{name}' already exists")

        # If setting as active, deactivate others
        if is_active:
            for conn in data.get("connections", []):
                conn["is_active"] = False

        new_connection = {
            "name": name,
            "host": host,
            "port": port,
            "service_name": service_name,
            "username": username,
            "password": password,  # Encrypted in file
            "is_active": is_active,
            "description": description,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        data.setdefault("connections", []).append(new_connection)
        self._write_connections(data)

        return new_connection

    def update_connection(
        self,
        name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        service_name: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        is_active: Optional[bool] = None,
        description: Optional[str] = None,
        new_name: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Update an existing connection configuration.

        Args:
            name: Connection name to update
            host: New Oracle host
            port: New Oracle port
            service_name: New Oracle service name
            username: New database username
            password: New database password
            is_active: Whether this is the active connection
            description: New description
            new_name: Rename the connection

        Returns:
            Updated connection dictionary or None if not found.
        """
        data = self._read_connections()

        # Check if new_name already exists (if renaming)
        if new_name:
            for conn in data.get("connections", []):
                if conn.get("name") == new_name and conn.get("name") != name:
                    raise ValueError(f"Connection with name '{new_name}' already exists")

        updated_conn = None
        for conn in data.get("connections", []):
            if conn.get("name") == name:
                if host is not None:
                    conn["host"] = host
                if port is not None:
                    conn["port"] = port
                if service_name is not None:
                    conn["service_name"] = service_name
                if username is not None:
                    conn["username"] = username
                if password is not None:
                    conn["password"] = password
                if description is not None:
                    conn["description"] = description
                if new_name is not None:
                    conn["name"] = new_name
                if is_active is not None:
                    # If setting as active, deactivate others
                    if is_active:
                        for other_conn in data.get("connections", []):
                            if other_conn.get("name") != conn.get("name"):
                                other_conn["is_active"] = False
                    conn["is_active"] = is_active

                conn["updated_at"] = datetime.utcnow().isoformat()
                updated_conn = conn
                break

        if updated_conn:
            self._write_connections(data)

        return updated_conn

    def delete_connection(self, name: str) -> bool:
        """
        Delete a connection configuration.

        Args:
            name: Connection name to delete

        Returns:
            True if deleted, False if not found.
        """
        data = self._read_connections()
        original_count = len(data.get("connections", []))

        data["connections"] = [
            conn for conn in data.get("connections", []) if conn.get("name") != name
        ]

        if len(data["connections"]) < original_count:
            self._write_connections(data)
            return True

        return False

    def set_active_connection(self, name: str) -> Optional[dict]:
        """
        Set a connection as the active connection.

        Args:
            name: Connection name to activate

        Returns:
            Activated connection dictionary or None if not found.
        """
        return self.update_connection(name, is_active=True)

    def get_sqlalchemy_url(self, connection_name: Optional[str] = None) -> Optional[str]:
        """
        Get SQLAlchemy connection URL for a specific or the active connection.

        Args:
            connection_name: Optional connection name. Uses active connection if None.

        Returns:
            SQLAlchemy connection URL string or None if no connection found.
        """
        if connection_name:
            conn = self.get_connection(connection_name)
        else:
            conn = self.get_active_connection()

        if not conn:
            return None

        return (
            f"oracle+oracledb://{conn['username']}:{conn['password']}"
            f"@{conn['host']}:{conn['port']}/?service_name={conn['service_name']}"
        )

    def connection_exists(self, name: str) -> bool:
        """Check if a connection with the given name exists."""
        return self.get_connection(name) is not None

    def get_connection_without_password(self, name: str) -> Optional[dict]:
        """
        Get a connection without the password field (for API responses).

        Args:
            name: Connection name

        Returns:
            Connection dictionary without password or None if not found.
        """
        conn = self.get_connection(name)
        if conn:
            return {k: v for k, v in conn.items() if k != "password"}
        return None

    def get_all_connections_without_passwords(self) -> list[dict]:
        """
        Get all connections without password fields (for API responses).

        Returns:
            List of connection dictionaries without passwords.
        """
        connections = self.get_all_connections()
        return [{k: v for k, v in conn.items() if k != "password"} for conn in connections]


# Singleton instance for use across the application
connection_service = ConnectionFileService()
