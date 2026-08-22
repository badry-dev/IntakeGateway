"""Shared fixtures for unit tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def sqlite_dest_factory():
    """Factory for in-memory SQLite destination sessions.

    Uses StaticPool so the setup connection and the yielded session share one
    DBAPI connection — required for deterministic savepoint/rollback behavior.
    """
    engines_sessions = []

    def _make(ddl: str):
        from sqlalchemy import text

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        conn = engine.connect()
        conn.execute(text(ddl))
        conn.commit()
        session = sessionmaker(bind=conn)()
        engines_sessions.append((session, conn, engine))
        return session

    yield _make

    for session, conn, engine in engines_sessions:
        session.close()
        conn.close()
        engine.dispose()
