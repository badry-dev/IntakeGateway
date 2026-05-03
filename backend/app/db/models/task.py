from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text  # noqa: F401
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
    )  # Legacy: OAuth settings (deprecated; superseded by columns below)

    # OAuth2 grant + token cache (P0-A). client_secret/access_token/refresh_token are Fernet-encrypted at rest.
    oauth_grant_type = Column(
        String(30), nullable=True
    )  # 'static' | 'client_credentials' | 'refresh_token'
    oauth_token_url = Column(String(1000), nullable=True)
    oauth_client_id = Column(String(500), nullable=True)
    # Text rather than String(N) — Fernet ciphertext expands plaintext by ~38%
    # before base64, and real-world OAuth tokens (Microsoft, Google, AWS) can
    # exceed 1500 chars plaintext, putting encrypted forms over a 2000 limit.
    # Storing as Text avoids silent truncation that would corrupt the token.
    oauth_client_secret = Column(Text, nullable=True)  # Encrypted
    oauth_scope = Column(String(500), nullable=True)
    oauth_audience = Column(String(500), nullable=True)
    oauth_access_token = Column(Text, nullable=True)  # Encrypted server-managed cache
    oauth_refresh_token = Column(Text, nullable=True)  # Encrypted
    oauth_token_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Rate-limit / 429 handling (P0-B). NULL means use Settings defaults.
    rate_limit_max_retries = Column(Integer, nullable=True)
    rate_limit_max_wait_seconds = Column(Integer, nullable=True)
    rate_limit_rps = Column(Integer, nullable=True)  # Stored only; declarative for v1.

    # Cursor / incremental fetch (P0-C). Watermark advances only on non-backfill, non-replay successful runs.
    cursor_field = Column(String(200), nullable=True)
    cursor_param_name = Column(String(200), nullable=True)
    cursor_initial_value = Column(String(500), nullable=True)
    cursor_last_value = Column(String(500), nullable=True)

    # Upsert configuration (Phase 8)
    upsert_enabled = Column(Boolean, nullable=False, default=False)
    upsert_keys = Column(JSONText, nullable=True)  # JSON array of column names for matching
    skip_column = Column(String(100), nullable=True)  # Column to check for skip condition
    skip_value = Column(String(100), nullable=True)  # Value that triggers skip (e.g., 'Y')
    continue_on_error = Column(
        Boolean, nullable=False, default=True
    )  # Continue processing on row errors

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
