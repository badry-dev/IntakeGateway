from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from app.db.session import Base
from app.db.types import ID_TYPE, JSONText


class Task(Base):
    __tablename__ = "task"
    id = Column(ID_TYPE, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    connection_id = Column(String(64), nullable=True)
    http_method = Column(String(10), nullable=False, default="GET")
    endpoint_path = Column(String(1000), nullable=False)
    query_params_json = Column(JSONText, nullable=True)
    headers_json = Column(JSONText, nullable=True)
    body_json = Column(JSONText, nullable=True)
    record_path = Column(String(400), nullable=True)
    dest_table = Column(String(200), nullable=False)
    batch_size = Column(Integer, nullable=False, default=500)
    is_active = Column(Boolean, nullable=False, default=True)

    # Authentication fields (Phase 7)
    auth_type = Column(
        String(20), nullable=True, default="none"
    )  # 'none', 'bearer', 'api_key', 'basic', 'oauth'
    api_key = Column(String(500), nullable=True)  # Encrypted
    username = Column(String(200), nullable=True)  # For Basic auth
    password = Column(String(500), nullable=True)  # Encrypted
    oauth_config = Column(
        JSONText, nullable=True
    )  # OAuth settings (client_id, token_url, etc.)

    # Upsert configuration (Phase 8)
    upsert_enabled = Column(Boolean, nullable=False, default=False)
    upsert_keys = Column(
        JSONText, nullable=True
    )  # JSON array of column names for matching
    skip_column = Column(
        String(100), nullable=True
    )  # Column to check for skip condition
    skip_value = Column(
        String(100), nullable=True
    )  # Value that triggers skip (e.g., 'Y')
    continue_on_error = Column(
        Boolean, nullable=False, default=True
    )  # Continue processing on row errors

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
