from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


engine_kwargs = {
    "future": True,
    "pool_pre_ping": True,
}

if settings.APP_DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs["pool_size"] = 5
    engine_kwargs["max_overflow"] = 5

engine = create_engine(settings.APP_DATABASE_URL, **engine_kwargs)
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
