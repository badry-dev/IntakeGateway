"""
Dynamic connection pool manager.

Manages SQLAlchemy engines per connection configuration.
Pools are created on-demand and cached for performance.
Supports Oracle, PostgreSQL, and MySQL databases.
"""

import time
from urllib.parse import quote_plus
import oracledb
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from loguru import logger
from app.services.connection_storage import get_connection_storage


# Cache of engines by connection_id
_engine_cache: dict[str, Engine] = {}
_session_factories: dict[str, sessionmaker] = {}
_oracle_client_attempted = False


def _ensure_oracle_client_initialized() -> None:
    """Try thick mode once, then quietly continue with thin mode."""
    global _oracle_client_attempted

    if _oracle_client_attempted:
        return

    _oracle_client_attempted = True

    try:
        oracledb.init_oracle_client(lib_dir=r"C:\oracle\instantclient_23_0")
        logger.info("Oracle client initialized in THICK mode")
    except Exception as exc:
        logger.info(f"Oracle thick mode unavailable, using thin mode: {exc}")


def build_connection_url(conn: dict, password: str) -> str:
    """
    Build SQLAlchemy connection URL from connection config.

    Args:
        conn: Connection configuration dict
        password: Decrypted password

    Returns:
        SQLAlchemy connection URL string

    Raises:
        ValueError: If db_type is not supported
    """
    db_type = conn.get("db_type", "oracle")
    host = conn.get("host", "localhost")
    port = conn.get("port", 1521)
    username = conn.get("username", "")

    # URL-encode password to handle special characters
    encoded_password = quote_plus(password)

    if db_type == "oracle":
        _ensure_oracle_client_initialized()
        service_name = conn.get("service_name", "ORCL")
        return (
            f"oracle+oracledb://{username}:{encoded_password}"
            f"@{host}:{port}/?service_name={service_name}"
        )
    elif db_type == "postgresql":
        database = conn.get("database", "postgres")
        return (
            f"postgresql+psycopg2://{username}:{encoded_password}"
            f"@{host}:{port}/{database}"
        )
    elif db_type == "mysql":
        database = conn.get("database", "")
        return f"mysql+pymysql://{username}:{encoded_password}@{host}:{port}/{database}"
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def get_engine(connection_id: str) -> Engine:
    """
    Get SQLAlchemy engine for a connection.

    Engines are cached for performance.

    Args:
        connection_id: Specific connection ID for the task

    Returns:
        SQLAlchemy Engine

    Raises:
        ValueError: If connection_id is missing or the specified connection is not found
    """
    if not connection_id:
        raise ValueError("connection_id is required")

    storage = get_connection_storage()
    conn = storage.get_connection(connection_id, include_password=True)
    if not conn:
        raise ValueError(f"Connection {connection_id} not found")

    # Return cached engine if available
    if connection_id in _engine_cache:
        logger.debug(f"Returning cached engine for connection {connection_id}")
        return _engine_cache[connection_id]

    # Create new engine
    password = storage.get_decrypted_password(connection_id)
    if not password:
        raise ValueError(f"Failed to decrypt password for connection {connection_id}")

    url = build_connection_url(conn, password)

    engine = create_engine(
        url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,  # Check connection health before use
        future=True,
    )

    _engine_cache[connection_id] = engine
    logger.info(f"Created connection pool for {conn['name']} ({connection_id})")

    return engine


def get_session(connection_id: str) -> Session:
    """
    Get a database session for a connection.

    Args:
        connection_id: Specific connection ID

    Returns:
        SQLAlchemy Session instance
    """
    engine = get_engine(connection_id)

    # Cache session factory
    if connection_id not in _session_factories:
        _session_factories[connection_id] = sessionmaker(
            autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
        )

    return _session_factories[connection_id]()


def invalidate_pool(connection_id: str) -> None:
    """
    Invalidate cached pool when connection is updated/deleted.

    Args:
        connection_id: ID of connection to invalidate
    """
    if connection_id in _engine_cache:
        try:
            _engine_cache[connection_id].dispose()
            logger.info(f"Disposed engine for connection {connection_id}")
        except Exception as e:
            logger.warning(f"Error disposing engine for {connection_id}: {e}")
        del _engine_cache[connection_id]

    if connection_id in _session_factories:
        del _session_factories[connection_id]

    logger.info(f"Invalidated connection pool for {connection_id}")


def test_connection(config: dict) -> dict:
    """
    Test a database connection without saving.

    Args:
        config: Connection configuration with plaintext password

    Returns:
        Dict with success, message, latency_ms, and server_version
    """
    password = config.get("password", "")
    test_config = {k: v for k, v in config.items() if k != "password"}

    try:
        if test_config.get("db_type", "oracle") == "oracle":
            _ensure_oracle_client_initialized()

        url = build_connection_url(test_config, password)

        # Create temporary engine with minimal pool
        test_engine = create_engine(
            url,
            pool_size=1,
            max_overflow=0,
            pool_timeout=10,
            connect_args={"connect_timeout": 10}
            if test_config.get("db_type") != "oracle"
            else {},
        )

        start = time.time()

        with test_engine.connect() as conn:
            db_type = test_config.get("db_type", "oracle")

            # Get server version based on database type
            if db_type == "oracle":
                result = conn.execute(
                    text("SELECT banner FROM v$version WHERE ROWNUM = 1")
                )
                version = result.scalar()
            elif db_type == "postgresql":
                result = conn.execute(text("SELECT version()"))
                version = result.scalar()
            elif db_type == "mysql":
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
            else:
                version = "Unknown"

        latency = int((time.time() - start) * 1000)

        # Cleanup
        test_engine.dispose()

        logger.info(
            f"Connection test successful: {test_config.get('host')}:{test_config.get('port')}"
        )

        return {
            "success": True,
            "message": "Connection successful",
            "latency_ms": latency,
            "server_version": str(version) if version else None,
        }

    except Exception as e:
        error_msg = str(e)
        # Sanitize error message to not expose sensitive info
        if "password" in error_msg.lower():
            error_msg = "Authentication failed - please check credentials"

        logger.error(f"Connection test failed for {test_config.get('host')}: {e}")

        return {
            "success": False,
            "message": error_msg,
            "latency_ms": None,
            "server_version": None,
        }


def get_all_engines() -> dict[str, Engine]:
    """
    Get all cached engines (for debugging/monitoring).

    Returns:
        Dict of connection_id -> Engine
    """
    return dict(_engine_cache)


def clear_all_pools() -> None:
    """
    Clear all cached connection pools.

    Use with caution - primarily for testing or shutdown.
    """
    for conn_id, engine in list(_engine_cache.items()):
        try:
            engine.dispose()
        except Exception as e:
            logger.warning(f"Error disposing engine {conn_id}: {e}")

    _engine_cache.clear()
    _session_factories.clear()
    logger.info("Cleared all connection pools")
