from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.sql import func

from app.db.session import Base
from app.db.types import ID_TYPE


class ColumnMapping(Base):
    __tablename__ = "column_mapping"

    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    task_id = Column(ID_TYPE, ForeignKey("task.id", ondelete="CASCADE"), nullable=False, index=True)
    source_field = Column(String(255), nullable=False)  # from API response
    dest_column = Column(String(255), nullable=False)  # Oracle table column
    transform_rules = Column(Text, nullable=True)  # JSON string with transform configs
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
