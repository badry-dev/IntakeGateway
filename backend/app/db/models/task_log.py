from sqlalchemy import Column, DateTime, String, ForeignKey
from sqlalchemy.sql import func
from app.db.session import Base
from app.db.types import ID_TYPE, JSONText


class TaskLog(Base):
    __tablename__ = "task_log"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    task_run_id = Column(
        ID_TYPE,
        ForeignKey("task_run.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_name = Column(
        String(50), nullable=True
    )  # FETCH_API, MAP_RECORDS, VALIDATE, INSERT_DB, etc.
    message = Column(String(1000), nullable=True)
    details = Column(JSONText, nullable=True)  # JSON with additional details
    created_at = Column(DateTime(timezone=True), server_default=func.now())
