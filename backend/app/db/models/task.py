
from sqlalchemy import BigInteger, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func
from sqlalchemy.types import TypeDecorator
import json
from app.db.session import Base

class JSONEncodedDict(TypeDecorator):
    """Represents an immutable structure as a JSON-encoded string for Oracle compatibility."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return json.dumps(value)
        return None

    def process_result_value(self, value, dialect):
        if value is not None:
            return json.loads(value)
        return None

class Task(Base):
    __tablename__ = "task"
    id = Column(BigInteger, primary_key=True)
    name = Column(String(200), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    connection_id = Column(BigInteger, nullable=True)
    http_method = Column(String(10), nullable=False, default="GET")
    endpoint_path = Column(String(1000), nullable=False)
    query_params_json = Column(JSONEncodedDict, nullable=True)
    headers_json = Column(JSONEncodedDict, nullable=True)
    body_json = Column(JSONEncodedDict, nullable=True)
    record_path = Column(String(400), nullable=True)
    dest_table = Column(String(200), nullable=False)
    batch_size = Column(Integer, nullable=False, default=500)
    is_active = Column(Boolean, nullable=False, default=True)
    
    # Authentication fields (Phase 7)
    auth_type = Column(String(20), nullable=True, default='none')  # 'none', 'bearer', 'api_key', 'basic', 'oauth'
    api_key = Column(String(500), nullable=True)  # Encrypted
    username = Column(String(200), nullable=True)  # For Basic auth
    password = Column(String(500), nullable=True)  # Encrypted
    oauth_config = Column(JSONEncodedDict, nullable=True)  # OAuth settings (client_id, token_url, etc.)

    # Upsert configuration (Phase 8)
    upsert_enabled = Column(Boolean, nullable=False, default=False)
    upsert_keys = Column(JSONEncodedDict, nullable=True)  # List of column names for matching (stored as JSON)
    skip_column = Column(String(100), nullable=True)  # Column to check for skip condition
    skip_value = Column(String(100), nullable=True)  # Value that triggers skip (e.g., 'Y')
    continue_on_error = Column(Boolean, nullable=False, default=True)  # Continue processing on row errors

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
