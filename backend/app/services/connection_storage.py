"""
Encrypted file storage service for database connections.

Stores connections in an encrypted JSON file using Fernet symmetric encryption.
File location is configurable via CONNECTIONS_FILE_PATH environment variable.
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from loguru import logger
from app.core.encryption import encrypt_value, decrypt_value, get_encryption_service


# Default path (can be overridden via environment variable)
DEFAULT_CONNECTIONS_PATH = os.getenv("CONNECTIONS_FILE_PATH", "connections.enc")


class ConnectionStorageService:
    """Service for managing encrypted connection storage"""

    def __init__(self, file_path: str = DEFAULT_CONNECTIONS_PATH):
        """
        Initialize storage service.

        Args:
            file_path: Path to encrypted connections file
        """
        self.file_path = Path(file_path)
        self._encryption = get_encryption_service()

    @staticmethod
    def _empty_data() -> dict:
        return {"version": 1, "connections": []}

    @classmethod
    def _normalize_data(cls, data: dict) -> dict:
        """Normalize persisted data and strip legacy default/active fields."""
        if not isinstance(data, dict):
            return cls._empty_data()

        connections = []
        for conn in data.get("connections", []):
            if not isinstance(conn, dict):
                continue
            normalized_conn = {k: v for k, v in conn.items() if k != "is_default"}
            connections.append(normalized_conn)

        version = data.get("version", 1)
        if not isinstance(version, int):
            version = 1

        return {
            "version": version,
            "connections": connections,
        }

    def _read_file(self) -> dict:
        """Read and decrypt connections file"""
        if not self.file_path.exists():
            logger.debug(
                f"Connections file not found at {self.file_path}, returning empty structure"
            )
            return self._empty_data()

        try:
            encrypted_content = self.file_path.read_text(encoding="utf-8")

            # Handle empty file
            if not encrypted_content or encrypted_content.strip() == "":
                logger.debug(
                    f"Empty connections file at {self.file_path}, returning empty structure"
                )
                return self._empty_data()

            decrypted = self._encryption.decrypt(encrypted_content)
            return self._normalize_data(json.loads(decrypted))
        except Exception as e:
            logger.error(
                f"Failed to read connections file at {self.file_path}: {e}. "
                "Treating destination connections as empty so the app remains usable."
            )
            return self._empty_data()

    def _write_file(self, data: dict) -> None:
        """Encrypt and write connections file"""
        try:
            json_str = json.dumps(data, indent=2, default=str)
            encrypted = self._encryption.encrypt(json_str)

            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write file
            self.file_path.write_text(encrypted, encoding="utf-8")

            # Set secure permissions on Unix systems
            if os.name != "nt":
                os.chmod(self.file_path, 0o600)
                logger.debug(f"Set file permissions to 600 for {self.file_path}")

            logger.debug(f"Wrote encrypted connections file to {self.file_path}")
        except Exception as e:
            logger.error(f"Failed to write connections file: {e}")
            raise ValueError(f"Failed to write connections file: {e}") from e

    def list_connections(self) -> dict:
        """
        List all connections with passwords masked.

        Returns:
            Dict with connections list and version
        """
        data = self._read_file()

        # Mask passwords in response
        masked_connections = []
        for conn in data.get("connections", []):
            masked_conn = {**conn}
            masked_conn["password"] = "********"
            masked_connections.append(masked_conn)

        return {"version": data.get("version", 1), "connections": masked_connections}

    def get_connection(
        self, connection_id: str, include_password: bool = False
    ) -> Optional[dict]:
        """
        Get a single connection by ID.

        Args:
            connection_id: Connection ID to retrieve
            include_password: If True, include encrypted password (internal use only)

        Returns:
            Connection dict or None if not found
        """
        data = self._read_file()

        for conn in data.get("connections", []):
            if conn.get("id") == connection_id:
                result = {**conn}
                if not include_password:
                    result["password"] = "********"
                return result

        return None

    def create_connection(self, connection_data: dict) -> dict:
        """
        Create a new connection.

        Args:
            connection_data: Connection configuration (including plaintext password)

        Returns:
            Created connection with masked password
        """
        data = self._read_file()
        now = datetime.now(timezone.utc).isoformat()

        # Generate ID and set metadata
        new_conn = {
            "id": str(uuid.uuid4()),
            "name": connection_data["name"],
            "db_type": connection_data.get("db_type", "oracle"),
            "host": connection_data["host"],
            "port": connection_data.get("port", 1521),
            "username": connection_data["username"],
            "password": encrypt_value(connection_data["password"]),
            "service_name": connection_data.get("service_name"),
            "database": connection_data.get("database"),
            "connection_options": connection_data.get("connection_options"),
            "created_at": now,
            "updated_at": now,
        }

        data["connections"].append(new_conn)

        self._write_file(data)
        logger.info(f"Created connection: {new_conn['name']} ({new_conn['id']})")

        # Return with masked password
        return {**new_conn, "password": "********"}

    def update_connection(self, connection_id: str, updates: dict) -> Optional[dict]:
        """
        Update an existing connection.

        Args:
            connection_id: ID of connection to update
            updates: Fields to update (password only updated if provided)

        Returns:
            Updated connection with masked password, or None if not found
        """
        data = self._read_file()

        for i, conn in enumerate(data.get("connections", [])):
            if conn.get("id") == connection_id:
                # Handle password update
                if "password" in updates and updates["password"]:
                    updates["password"] = encrypt_value(updates["password"])
                else:
                    updates.pop("password", None)

                # Merge updates
                data["connections"][i] = {
                    **conn,
                    **updates,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                self._write_file(data)
                logger.info(
                    f"Updated connection: {data['connections'][i]['name']} ({connection_id})"
                )

                # Return with masked password
                return {**data["connections"][i], "password": "********"}

        return None

    def delete_connection(self, connection_id: str) -> bool:
        """
        Delete a connection.

        Args:
            connection_id: ID of connection to delete

        Returns:
            True if deleted, False if not found
        """
        data = self._read_file()

        initial_count = len(data.get("connections", []))
        data["connections"] = [
            c for c in data.get("connections", []) if c.get("id") != connection_id
        ]

        if len(data["connections"]) < initial_count:
            self._write_file(data)
            logger.info(f"Deleted connection: {connection_id}")
            return True

        return False

    def get_decrypted_password(self, connection_id: str) -> Optional[str]:
        """
        Get decrypted password for a connection.

        WARNING: Internal use only. Never expose this in API responses.

        Args:
            connection_id: ID of connection

        Returns:
            Decrypted password or None if connection not found
        """
        data = self._read_file()

        for conn in data.get("connections", []):
            if conn.get("id") == connection_id:
                encrypted_password = conn.get("password")
                if encrypted_password:
                    return decrypt_value(encrypted_password)
                return None

        return None


# Singleton instance
_storage_service: Optional[ConnectionStorageService] = None


def get_connection_storage() -> ConnectionStorageService:
    """
    Get singleton storage service instance.

    Returns:
        Global ConnectionStorageService instance
    """
    global _storage_service
    if _storage_service is None:
        _storage_service = ConnectionStorageService()
    return _storage_service
