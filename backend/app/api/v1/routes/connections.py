"""
Database connection management API routes.

Provides CRUD operations for database connections with encrypted storage.
Connections are tested before saving to prevent invalid configurations.
"""

from fastapi import APIRouter, HTTPException
from loguru import logger
from app.db.schemas.connection import (
    ConnectionCreate,
    ConnectionUpdate,
    ConnectionOut,
    ConnectionListOut,
    ConnectionTestRequest,
    ConnectionTestResult,
)
from app.services.connection_storage import get_connection_storage
from app.services.connection_pool import test_connection, invalidate_pool
from datetime import datetime


router = APIRouter(prefix="/api/v1/connections", tags=["connections"])


def _parse_datetime(dt_value) -> datetime:
    """Parse datetime from string or return as-is if already datetime"""
    if isinstance(dt_value, str):
        # Handle ISO format with or without timezone
        if dt_value.endswith("Z"):
            dt_value = dt_value[:-1] + "+00:00"
        return datetime.fromisoformat(dt_value)
    return dt_value


def _connection_to_out(conn: dict) -> ConnectionOut:
    """Convert connection dict to ConnectionOut schema"""
    return ConnectionOut(
        id=conn["id"],
        name=conn["name"],
        db_type=conn.get("db_type", "oracle"),
        host=conn["host"],
        port=conn.get("port", 1521),
        username=conn["username"],
        service_name=conn.get("service_name"),
        database=conn.get("database"),
        connection_options=conn.get("connection_options"),
        created_at=_parse_datetime(conn["created_at"]),
        updated_at=_parse_datetime(conn["updated_at"]),
    )


@router.get("/", response_model=ConnectionListOut)
def list_connections():
    """
    List all configured database connections.

    Passwords are masked in the response for security.
    Returns the saved connections and total count.
    """
    storage = get_connection_storage()
    data = storage.list_connections()

    connections = [_connection_to_out(c) for c in data.get("connections", [])]

    return ConnectionListOut(connections=connections, total_count=len(connections))


@router.get("/{connection_id}", response_model=ConnectionOut)
def get_connection(connection_id: str):
    """
    Get a specific connection by ID.

    Args:
        connection_id: UUID of the connection

    Returns:
        Connection details (password masked)

    Raises:
        404: Connection not found
    """
    storage = get_connection_storage()
    conn = storage.get_connection(connection_id)

    if not conn:
        raise HTTPException(
            status_code=404, detail=f"Connection {connection_id} not found"
        )

    return _connection_to_out(conn)


@router.post("/", response_model=ConnectionOut, status_code=201)
def create_connection(payload: ConnectionCreate):
    """
    Create a new database connection.

    The connection is tested before saving. If the test fails,
    a 400 error is returned with the failure message.

    Args:
        payload: Connection configuration including password

    Returns:
        Created connection (password masked)

    Raises:
        400: Connection test failed
    """
    # Test connection before saving
    test_result = test_connection(
        {
            "db_type": payload.db_type,
            "host": payload.host,
            "port": payload.port,
            "username": payload.username,
            "password": payload.password,
            "service_name": payload.service_name,
            "database": payload.database,
        }
    )

    if not test_result["success"]:
        logger.warning(
            f"Connection test failed for {payload.name}: {test_result['message']}"
        )
        raise HTTPException(
            status_code=400, detail=f"Connection test failed: {test_result['message']}"
        )

    storage = get_connection_storage()
    conn = storage.create_connection(payload.model_dump())

    logger.info(f"Created connection: {conn['name']} ({conn['id']})")
    return _connection_to_out(conn)


@router.put("/{connection_id}", response_model=ConnectionOut)
def update_connection(connection_id: str, payload: ConnectionUpdate):
    """
    Update an existing connection.

    Only provided fields are updated. Password is only updated if provided.
    If connection details (host, port, credentials) change, the connection
    is re-tested before saving.

    Args:
        connection_id: UUID of the connection to update
        payload: Fields to update

    Returns:
        Updated connection (password masked)

    Raises:
        400: Connection test failed
        404: Connection not found
    """
    storage = get_connection_storage()

    # Verify exists
    existing = storage.get_connection(connection_id, include_password=True)
    if not existing:
        raise HTTPException(
            status_code=404, detail=f"Connection {connection_id} not found"
        )

    updates = payload.model_dump(exclude_unset=True)

    # If connection details changed, test new connection
    connection_fields = {
        "host",
        "port",
        "username",
        "password",
        "service_name",
        "database",
        "db_type",
    }
    if any(k in updates for k in connection_fields):
        # Merge with existing for test
        test_config = {
            "db_type": updates.get("db_type", existing.get("db_type", "oracle")),
            "host": updates.get("host", existing["host"]),
            "port": updates.get("port", existing.get("port", 1521)),
            "username": updates.get("username", existing["username"]),
            "password": updates.get("password")
            or storage.get_decrypted_password(connection_id),
            "service_name": updates.get("service_name", existing.get("service_name")),
            "database": updates.get("database", existing.get("database")),
        }

        test_result = test_connection(test_config)
        if not test_result["success"]:
            logger.warning(
                f"Connection test failed during update for {connection_id}: {test_result['message']}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Connection test failed: {test_result['message']}",
            )

        # Invalidate cached pool since connection details changed
        invalidate_pool(connection_id)

    conn = storage.update_connection(connection_id, updates)
    if not conn:
        raise HTTPException(
            status_code=404, detail=f"Connection {connection_id} not found"
        )

    logger.info(f"Updated connection: {conn['name']} ({conn['id']})")
    return _connection_to_out(conn)


@router.delete("/{connection_id}", status_code=204)
def delete_connection(connection_id: str):
    """
    Delete a connection.

    Args:
        connection_id: UUID of the connection to delete

    Raises:
        404: Connection not found
    """
    storage = get_connection_storage()

    if not storage.delete_connection(connection_id):
        raise HTTPException(
            status_code=404, detail=f"Connection {connection_id} not found"
        )

    invalidate_pool(connection_id)
    logger.info(f"Deleted connection: {connection_id}")


@router.post("/test", response_model=ConnectionTestResult)
def test_connection_endpoint(payload: ConnectionTestRequest):
    """
    Test a database connection without saving.

    Use this to validate connection parameters before creating
    or updating a connection.

    Args:
        payload: Connection configuration to test

    Returns:
        Test result with success status, message, latency, and server version
    """
    result = test_connection(payload.model_dump())
    return ConnectionTestResult(**result)
