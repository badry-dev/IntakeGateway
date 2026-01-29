from sqlalchemy import BigInteger, Column, DateTime, String, Text, ForeignKey, Integer
from sqlalchemy.sql import func
from app.db.session import Base


class TaskLog(Base):
    __tablename__ = "task_log"
    
    id = Column(BigInteger, primary_key=True)
    task_run_id = Column(BigInteger, ForeignKey("task_run.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(50), nullable=True)  # FETCH_API, MAP_RECORDS, VALIDATE, INSERT_DB, etc.
    message = Column(String(1000), nullable=True)
    details = Column(Text, nullable=True)  # JSON with additional details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
