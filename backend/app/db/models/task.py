
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text, JSON
from sqlalchemy.sql import func
from app.db.session import Base

class Task(Base):
    __tablename__ = "task"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    connection_id = Column(BigInteger, nullable=True)
    http_method = Column(String(10), nullable=False, default="GET")
    endpoint_path = Column(String(1000), nullable=False)
    query_params_json = Column(JSON, nullable=True)
    headers_json = Column(JSON, nullable=True)
    body_json = Column(JSON, nullable=True)
    record_path = Column(String(400), nullable=True)
    dest_table = Column(String(200), nullable=False)
    batch_size = Column(Integer, nullable=False, default=500)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
