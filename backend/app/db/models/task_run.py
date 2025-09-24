
from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.sql import func
from app.db.session import Base

class TaskRun(Base):
    __tablename__ = "task_run"
    id = Column(BigInteger, primary_key=True)
    task_id = Column(BigInteger, nullable=False, index=True)
    status = Column(String(30), nullable=False, default="PENDING")
    rows_fetched = Column(Integer, default=0)
    rows_inserted = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
