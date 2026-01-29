
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
    completed_at = Column(DateTime(timezone=True), nullable=True)
    records_fetched = Column(Integer, default=0)
    records_inserted = Column(Integer, default=0)
    records_failed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
