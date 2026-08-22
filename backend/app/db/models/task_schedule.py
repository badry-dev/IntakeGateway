from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.db.session import Base
from app.db.types import ID_TYPE


class TaskSchedule(Base):
    __tablename__ = "task_schedule"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id = Column(ID_TYPE, ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    cron_expression = Column(String(50), nullable=False)  # e.g., "0 2 * * *" (2 AM daily)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    last_run_date = Column(DateTime(timezone=True), nullable=True)
    next_run_date = Column(DateTime(timezone=True), nullable=True)
    # Number of consecutive dispatch failures for this schedule; reset to 0 on
    # a successful enqueue. Persisted in its own transaction after rollback so
    # the counter survives the error path.
    consecutive_failures = Column(Integer, nullable=False, server_default="0", default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
