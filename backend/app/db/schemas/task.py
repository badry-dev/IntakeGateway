
from pydantic import BaseModel, Field, field_validator
from typing import Any, Optional, Literal
from datetime import datetime

class TaskCreate(BaseModel):
    name: str
    description: Optional[str] = None
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
    details: Optional[str] = None
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
    error_count: int
    warning_count: int = 0
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
    total_errors: int
    avg_duration_seconds: float
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
