
from enum import Enum
from sqlalchemy import BigInteger, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.session import Base


class TaskStatus(str, Enum):
    """Task run status enum"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"


class TaskRun(Base):
    __tablename__ = "task_run"
    id = Column(BigInteger, primary_key=True)
    task_id = Column(BigInteger, nullable=False, index=True)
    status = Column(String(30), nullable=False, default=TaskStatus.PENDING.value)
    started_at = Column(DateTime(timezone=True), nullable=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    rows_fetched = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    rows_updated = Column(Integer, default=0)  # Phase 8: Upsert updates
    rows_skipped = Column(Integer, default=0)  # Phase 8: Skipped due to skip condition
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
