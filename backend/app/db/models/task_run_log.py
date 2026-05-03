from sqlalchemy import Column, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.sql import func
from app.db.session import Base
from app.db.types import ID_TYPE


class TaskRunLog(Base):
    __tablename__ = "task_run_log"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    task_run_id = Column(
        ID_TYPE,
        ForeignKey("task_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    row_number = Column(Integer, nullable=True)  # NULL if log entry is not row-specific
    column_name = Column(String(255), nullable=True)
    error_type = Column(
        String(50), nullable=True
    )  # REQUIRED_FIELD, VALIDATION_FAILED, TYPE_MISMATCH, etc.
    error_message = Column(String(1000), nullable=True)
    source_value = Column(Text, nullable=True)  # What value was attempted
    created_at = Column(DateTime(timezone=True), server_default=func.now())
