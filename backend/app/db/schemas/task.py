import re
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Reusable regex for safe API parameter / column identifiers (cursor injection guard).
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")


class OAuthConfigIn(BaseModel):
    """OAuth2 configuration for client_credentials / refresh_token grants."""

    grant_type: Literal["static", "client_credentials", "refresh_token"] = "static"
    token_url: str | None = None
    client_id: str | None = None
    client_secret: str | None = None  # Encrypted before storage
    scope: str | None = None
    audience: str | None = None
    # Static-token migration path (back-compat with legacy oauth_config['access_token'])
    access_token: str | None = None
    refresh_token: str | None = None

    @model_validator(mode="after")
    def validate_grant_requirements(self):
        """Reject incomplete OAuth configs at request time so the worker
        doesn't fail later with a useless error. Each grant has different
        required fields per RFC 6749."""
        if self.grant_type == "client_credentials":
            missing = [
                f
                for f, v in (
                    ("token_url", self.token_url),
                    ("client_id", self.client_id),
                    ("client_secret", self.client_secret),
                )
                if not v
            ]
            if missing:
                raise ValueError(f"grant_type=client_credentials requires: {', '.join(missing)}")
        elif self.grant_type == "refresh_token":
            missing = [
                f
                for f, v in (
                    ("token_url", self.token_url),
                    ("refresh_token", self.refresh_token),
                )
                if not v
            ]
            if missing:
                raise ValueError(f"grant_type=refresh_token requires: {', '.join(missing)}")
        elif self.grant_type == "static":
            # Static needs an access_token via this submodel OR via the legacy
            # oauth_config dict. We only enforce when the submodel is provided
            # standalone — the legacy path is checked at runtime.
            if self.access_token is None and self.refresh_token is None:
                # Empty static block is permitted (back-compat with legacy
                # oauth_config). Skip the check rather than 422 a request that
                # will be resolved by the legacy path.
                pass
        return self


class RateLimitConfigIn(BaseModel):
    """Per-task rate-limit / 429 retry tuning."""

    max_retries: int | None = Field(default=None, ge=0, le=20)
    max_wait_seconds: int | None = Field(default=None, ge=0, le=3600)
    rps: int | None = Field(default=None, ge=0, le=1000)


class CursorConfigIn(BaseModel):
    """Cursor / incremental fetch configuration."""

    field: str | None = None
    param_name: str | None = None
    initial_value: str | None = None

    @field_validator("field", "param_name")
    @classmethod
    def validate_identifier(cls, v: str | None):
        if v is not None and not _SAFE_IDENTIFIER_RE.match(v):
            raise ValueError(
                "must match ^[A-Za-z_][A-Za-z0-9_]{0,99}$ "
                "(prevents URL/header injection via cursor params)"
            )
        return v

    @model_validator(mode="after")
    def validate_consistency(self):
        """Both `field` (response key to read) and `param_name` (request query
        param to inject) are required together — supplying only one silently
        disables half of the cursor flow at runtime, which is far worse than
        a 422 at config time."""
        if bool(self.field) != bool(self.param_name):
            raise ValueError(
                "cursor.field and cursor.param_name must be provided together "
                "(or both omitted to disable cursor support)"
            )
        if self.initial_value is not None and not self.field:
            raise ValueError("cursor.initial_value requires cursor.field and cursor.param_name")
        return self


class BackfillRequest(BaseModel):
    """Request body for POST /tasks/{id}/backfill."""

    cursor_start: str = Field(..., min_length=1, max_length=500)
    cursor_end: str | None = Field(default=None, max_length=500)


class ReplayRequest(BaseModel):
    """Request body for POST /runs/{run_id}/replay."""

    force: bool = False


class BackfillResponse(BaseModel):
    """202 response shape for POST /tasks/{id}/backfill."""

    status: str
    task_id: int
    is_backfill: bool = True
    cursor_start: str
    cursor_end: str | None = None
    celery_task_id: str | None = None


class ReplayResponse(BaseModel):
    """202 response shape for POST /runs/{run_id}/replay."""

    status: str
    task_id: int
    replay_of_run_id: int
    cursor_start: str | None = None
    cursor_end: str | None = None
    force: bool = False
    celery_task_id: str | None = None


class TaskCreate(BaseModel):
    name: str
    description: str | None = None
    connection_id: str = Field(..., min_length=1)
    http_method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH)$")
    endpoint_path: str
    query_params_json: dict[str, Any] | None = None
    headers_json: dict[str, Any] | None = None
    body_json: dict[str, Any] | None = None
    record_path: str | None = None
    dest_table: str
    batch_size: int = 500
    is_active: bool = True

    # Authentication fields (Phase 7)
    auth_type: Literal["none", "bearer", "api_key", "basic", "oauth"] = "none"
    api_key: str | None = None  # Will be encrypted before storage
    username: str | None = None  # For Basic auth
    password: str | None = None  # Will be encrypted before storage
    oauth_config: dict[str, Any] | None = None  # Legacy free-form (deprecated)

    # Structured OAuth / rate-limit / cursor config (P0)
    oauth: OAuthConfigIn | None = None
    rate_limit: RateLimitConfigIn | None = None
    cursor: CursorConfigIn | None = None

    # Upsert configuration (Phase 8)
    upsert_enabled: bool = False
    upsert_keys: list[str] | None = None  # Column names for matching
    skip_column: str | None = None  # Column to check for skip condition
    skip_value: str | None = None  # Value that triggers skip (e.g., 'Y')
    continue_on_error: bool = True  # Continue processing on row errors

    @field_validator("upsert_keys")
    @classmethod
    def validate_upsert_keys(cls, v: list[str] | None, info):
        """Validate that upsert_keys is provided when upsert is enabled"""
        upsert_enabled = info.data.get("upsert_enabled")
        if upsert_enabled and (not v or len(v) == 0):
            raise ValueError("upsert_enabled requires at least one column in upsert_keys")
        return v

    @field_validator("api_key")
    @classmethod
    def validate_api_key_with_auth_type(cls, v: str | None, info):
        """Validate that api_key is provided when needed"""
        auth_type = info.data.get("auth_type")
        if auth_type in ("bearer", "api_key") and not v:
            raise ValueError(f"{auth_type} authentication requires api_key")
        return v

    @field_validator("username", "password")
    @classmethod
    def validate_basic_auth(cls, v: str | None, info):
        """Validate that username/password are provided for basic auth"""
        auth_type = info.data.get("auth_type")
        if auth_type == "basic" and not v:
            raise ValueError("basic authentication requires both username and password")
        return v


class TaskOut(BaseModel):
    """Task response model - excludes sensitive authentication data"""

    id: int
    name: str
    description: str | None = None
    connection_id: str | None = None
    http_method: str
    endpoint_path: str
    query_params_json: dict[str, Any] | None = None
    headers_json: dict[str, Any] | None = None
    body_json: dict[str, Any] | None = None
    record_path: str | None = None
    dest_table: str
    batch_size: int
    is_active: bool

    # Authentication fields (safe ones only - no passwords/keys in response)
    auth_type: str = "none"
    username: str | None = None  # Safe to expose
    # api_key and password are NOT included in response

    # OAuth2 metadata (safe fields only — secrets never returned)
    oauth_grant_type: str | None = None
    oauth_token_url: str | None = None
    oauth_client_id: str | None = None
    oauth_scope: str | None = None
    oauth_audience: str | None = None
    oauth_token_expires_at: datetime | None = None
    # oauth_client_secret / oauth_access_token / oauth_refresh_token are NEVER serialized

    # Rate-limit / 429 tuning (safe to return)
    rate_limit_max_retries: int | None = None
    rate_limit_max_wait_seconds: int | None = None
    rate_limit_rps: int | None = None

    # Cursor state (safe to return — last_value is a watermark, not a secret)
    cursor_field: str | None = None
    cursor_param_name: str | None = None
    cursor_initial_value: str | None = None
    cursor_last_value: str | None = None

    # Upsert configuration (Phase 8)
    upsert_enabled: bool = False
    upsert_keys: list[str] | None = None
    skip_column: str | None = None
    skip_value: str | None = None
    continue_on_error: bool = True

    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class TaskLogOut(BaseModel):
    """Task execution log entry"""

    id: int
    task_run_id: int
    step_name: str
    message: str
    details: Any | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskRunLogOut(BaseModel):
    """Row-level error log entry"""

    id: int
    task_run_id: int
    row_number: int
    column_name: str
    error_type: str
    error_message: str
    source_value: str | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskRunOut(BaseModel):
    """Complete task run with all logs and results"""

    id: int
    task_id: int
    task_name: str | None = None
    is_retry: bool | None = None
    retry_of_run_id: int | None = None
    status: str
    rows_fetched: int
    rows_inserted: int
    rows_updated: int = 0  # Phase 8: Upsert updates
    rows_skipped: int = 0  # Phase 8: Skipped due to skip condition
    error_count: int
    warning_count: int = 0
    error_message: str | None = None
    started_at: datetime
    ended_at: datetime | None = None
    # Cursor / replay tracking (P0-C)
    cursor_start: str | None = None
    cursor_end: str | None = None
    is_backfill: bool = False
    is_replay: bool = False
    replay_of_run_id: int | None = None
    execution_logs: list[TaskLogOut] = []
    row_errors: list[TaskRunLogOut] = []

    model_config = ConfigDict(from_attributes=True)


class TaskWithAuthOut(TaskOut):
    """Task with authentication fields (for internal use only, don't expose api_key/password)"""

    # For internal endpoints that need auth info but still exclude sensitive fields
    pass


class TaskStatsOut(BaseModel):
    """Task execution statistics"""

    task_id: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float  # Percentage 0-100
    total_rows_fetched: int
    total_rows_inserted: int
    total_rows_updated: int = 0  # Phase 8: Upsert updates
    total_rows_skipped: int = 0  # Phase 8: Skipped rows
    total_errors: int
    avg_duration_seconds: float
    last_run_at: datetime | None = None
    last_run_status: str | None = None
