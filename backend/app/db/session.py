import logging

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine_kwargs = {
    "future": True,
    "pool_pre_ping": True,
}

_is_sqlite = settings.APP_DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 5

engine = create_engine(settings.APP_DATABASE_URL, **engine_kwargs)

if _is_sqlite:
    # The app DB is shared by the API, worker, and scheduler processes.
    # WAL + busy_timeout prevent the "database is locked" errors that the
    # default rollback-journal mode produces under concurrent writers.
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA busy_timeout=5000")
        finally:
            cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def init_app_database() -> None:
    """Create local app-state tables if they do not already exist."""
    import app.db.models.column_mapping  # noqa: F401
    import app.db.models.task  # noqa: F401
    import app.db.models.task_log  # noqa: F401
    import app.db.models.task_run  # noqa: F401
    import app.db.models.task_run_log  # noqa: F401
    import app.db.models.task_schedule  # noqa: F401

    Base.metadata.create_all(bind=engine)
    logger.info("App database initialized")


def get_db():
    """Dependency to get database session for FastAPI routes"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
