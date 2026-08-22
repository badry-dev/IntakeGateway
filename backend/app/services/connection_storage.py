"""
Encrypted file storage service for database connections.

Stores connections in an encrypted JSON file using Fernet symmetric encryption.
File location is configurable via CONNECTIONS_FILE_PATH environment variable.
"""

import json
import os
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path

from loguru import logger

from app.core.config import settings
from app.core.encryption import decrypt_value, encrypt_value, get_encryption_service

try:  # Unix
    import fcntl

    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - Windows
    fcntl = None
    _HAVE_FCNTL = False

try:  # Windows
    import msvcrt

    _HAVE_MSVCRT = True
except ImportError:  # pragma: no cover - non-Windows
    msvcrt = None
    _HAVE_MSVCRT = False

# Default path (can be overridden via environment variable)
DEFAULT_CONNECTIONS_PATH = os.getenv("CONNECTIONS_FILE_PATH", settings.CONNECTIONS_FILE_PATH)


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

    @contextmanager
    def _file_lock(self):
        """Cross-process advisory lock around read-modify-write cycles.

        The API, worker, and scheduler are separate processes sharing this
        file; without the lock their non-atomic read-modify-write cycles can
        lose each other's writes. Uses fcntl.flock on Unix and msvcrt.locking
        on Windows.
        """
        if not _HAVE_FCNTL and not _HAVE_MSVCRT:  # pragma: no cover
            # No interprocess locking primitive available. os.replace() keeps
            # the file intact, but concurrent writers can still lose updates —
            # refuse rather than corrupt silently.
            raise RuntimeError(
                "No interprocess file-locking primitive available on this "
                "platform; refusing unsynchronized connections-file access."
            )

        lock_path = self.file_path.with_suffix(self.file_path.suffix + ".lock")
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(lock_path, "w") as lock_file:
            if _HAVE_FCNTL:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            else:  # pragma: no cover - Windows
                msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lock_file.seek(0)
                    msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)

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
            # Preserve the unreadable file before treating the store as empty —
            # a silent reset previously made ALL saved connections vanish.
            backup_path = self.file_path.with_suffix(self.file_path.suffix + ".bak")
            try:
                if os.name != "nt":
                    # Create with owner-only permissions BEFORE writing: the
                    # unreadable source may contain partial secret data.
                    fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                    with os.fdopen(fd, "wb") as backup_file:
                        backup_file.write(self.file_path.read_bytes())
                else:  # pragma: no cover - Windows
                    backup_path.write_bytes(self.file_path.read_bytes())
                logger.error(
                    f"Failed to read connections file at {self.file_path}: {e}. "
                    f"A copy of the corrupt file was preserved at {backup_path}; "
                    "treating destination connections as empty so the app remains usable."
                )
            except Exception as backup_exc:
                logger.error(
                    f"Failed to read connections file at {self.file_path}: {e}. "
                    f"Additionally failed to preserve a backup: {backup_exc}"
                )
            return self._empty_data()

    def _write_file(self, data: dict) -> None:
        """Encrypt and atomically write connections file.

        Writes to a temp file in the same directory then os.replace()s it into
        place, so a crash mid-write can never leave a truncated/empty store
        behind (which previously read back as an empty connection list).
        """
        try:
            json_str = json.dumps(data, indent=2, default=str)
            encrypted = self._encryption.encrypt(json_str)

            # Ensure parent directory exists
            self.file_path.parent.mkdir(parents=True, exist_ok=True)

            # Atomic write: temp file + os.replace (same filesystem)
            import tempfile

            tmp_fd, tmp_name = tempfile.mkstemp(
                dir=self.file_path.parent, prefix=self.file_path.name, suffix=".tmp"
            )
            try:
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as tmp_file:
                    tmp_file.write(encrypted)
                    tmp_file.flush()
                    os.fsync(tmp_file.fileno())
                os.replace(tmp_name, self.file_path)
            except BaseException:
                try:
                    os.unlink(tmp_name)
                except OSError:
                    pass
                raise

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

    def get_connection(self, connection_id: str, include_password: bool = False) -> dict | None:
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
        now = datetime.now(UTC).isoformat()

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

        # The ENTIRE read-modify-write cycle holds the lock.
        with self._file_lock():
            data = self._read_file()
            data["connections"].append(new_conn)
            self._write_file(data)

        logger.info(f"Created connection: {new_conn['name']} ({new_conn['id']})")

        # Return with masked password
        return {**new_conn, "password": "********"}

    def update_connection(self, connection_id: str, updates: dict) -> dict | None:
        """
        Update an existing connection.

        Args:
            connection_id: ID of connection to update
            updates: Fields to update (password only updated if provided)

        Returns:
            Updated connection with masked password, or None if not found
        """
        with self._file_lock():
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
                        "updated_at": datetime.now(UTC).isoformat(),
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
        with self._file_lock():
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

    def get_decrypted_password(self, connection_id: str) -> str | None:
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
_storage_service: ConnectionStorageService | None = None


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
