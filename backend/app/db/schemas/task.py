
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional, Literal
from datetime import datetime

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connection_id: str = Field(..., min_length=1)
    http_method: str = Field(default="GET", pattern="^(GET|POST|PUT|PATCH)$")
    endpoint_path: str
    query_params_json: Optional[dict[str, Any]] = None
    headers_json: Optional[dict[str, Any]] = None
    body_json: Optional[dict[str, Any]] = None
    record_path: Optional[str] = None
    dest_table: str
    batch_size: int = 500
    is_active: bool = True
    
    # Authentication fields (Phase 7)
    auth_type: Literal['none', 'bearer', 'api_key', 'basic', 'oauth'] = 'none'
    api_key: Optional[str] = None  # Will be encrypted before storage
    username: Optional[str] = None  # For Basic auth
    password: Optional[str] = None  # Will be encrypted before storage
    oauth_config: Optional[dict[str, Any]] = None  # OAuth settings

    # Upsert configuration (Phase 8)
    upsert_enabled: bool = False
    upsert_keys: Optional[list[str]] = None  # Column names for matching
    skip_column: Optional[str] = None  # Column to check for skip condition
    skip_value: Optional[str] = None  # Value that triggers skip (e.g., 'Y')
    continue_on_error: bool = True  # Continue processing on row errors

    @field_validator('upsert_keys')
    @classmethod
    def validate_upsert_keys(cls, v: Optional[list[str]], info):
        """Validate that upsert_keys is provided when upsert is enabled"""
        upsert_enabled = info.data.get('upsert_enabled')
        if upsert_enabled and (not v or len(v) == 0):
            raise ValueError("upsert_enabled requires at least one column in upsert_keys")
        return v

    @field_validator('api_key')
    @classmethod
    def validate_api_key_with_auth_type(cls, v: Optional[str], info):
        """Validate that api_key is provided when needed"""
        auth_type = info.data.get('auth_type')
        if auth_type in ('bearer', 'api_key') and not v:
            raise ValueError(f"{auth_type} authentication requires api_key")
        return v
    
    @field_validator('username', 'password')
    @classmethod
    def validate_basic_auth(cls, v: Optional[str], info):
        """Validate that username/password are provided for basic auth"""
        auth_type = info.data.get('auth_type')
        if auth_type == 'basic' and not v:
            raise ValueError("basic authentication requires both username and password")
        return v

class TaskOut(BaseModel):
    """Task response model - excludes sensitive authentication data"""
    id: int
    name: str
    description: Optional[str] = None
    connection_id: Optional[str] = None
    http_method: str
    endpoint_path: str
    query_params_json: Optional[dict[str, Any]] = None
    headers_json: Optional[dict[str, Any]] = None
    body_json: Optional[dict[str, Any]] = None
    record_path: Optional[str] = None
    dest_table: str
    batch_size: int
    is_active: bool
    
    # Authentication fields (safe ones only - no passwords/keys in response)
    auth_type: str = 'none'
    username: Optional[str] = None  # Safe to expose
    # api_key and password are NOT included in response

    # Upsert configuration (Phase 8)
    upsert_enabled: bool = False
    upsert_keys: Optional[list[str]] = None
    skip_column: Optional[str] = None
    skip_value: Optional[str] = None
    continue_on_error: bool = True

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class TaskLogOut(BaseModel):
    """Task execution log entry"""
    id: int
    task_run_id: int
    step_name: str
    message: str
    details: Optional[Any] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskRunLogOut(BaseModel):
    """Row-level error log entry"""
    id: int
    task_run_id: int
    row_number: int
    column_name: str
    error_type: str
    error_message: str
    source_value: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskRunOut(BaseModel):
    """Complete task run with all logs and results"""
    id: int
    task_id: int
    task_name: Optional[str] = None
    is_retry: Optional[bool] = None
    retry_of_run_id: Optional[int] = None
    status: str
    rows_fetched: int
    rows_inserted: int
    rows_updated: int = 0  # Phase 8: Upsert updates
    rows_skipped: int = 0  # Phase 8: Skipped due to skip condition
    error_count: int
    warning_count: int = 0
    error_message: Optional[str] = None
    started_at: datetime
    ended_at: Optional[datetime] = None
    execution_logs: list[TaskLogOut] = []
    row_errors: list[TaskRunLogOut] = []
    
    class Config:
        from_attributes = True

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
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
