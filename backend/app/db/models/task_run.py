
from enum import Enum
from sqlalchemy import Boolean, Column, DateTime, Integer, String
from app.db.session import Base
from app.db.types import ID_TYPE


class TaskStatus(str, Enum):
    """Task run status enum"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class TaskRun(Base):
    __tablename__ = "task_run"
    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id = Column(ID_TYPE, nullable=False, index=True)
    status = Column(String(30), nullable=False, default=TaskStatus.PENDING.value)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    rows_fetched = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)  # Phase 8: Upsert updates
    rows_skipped = Column(Integer, default=0)  # Phase 8: Skipped due to skip condition
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    error_message = Column(String(2000), nullable=True)

    # Cursor + replay tracking (P0-C)
    cursor_start = Column(String(500), nullable=True)
    cursor_end = Column(String(500), nullable=True)
    is_backfill = Column(Boolean, nullable=False, default=False)
    is_replay = Column(Boolean, nullable=False, default=False)
    replay_of_run_id = Column(Integer, nullable=True)
