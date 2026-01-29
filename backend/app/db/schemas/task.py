
from pydantic import BaseModel, Field
from typing import Any, Optional
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

class TaskOut(TaskCreate):
    id: int
    class Config:
        from_attributes = True

class TaskLogOut(BaseModel):
    """Task execution log entry"""
    id: int
    task_id: int
    run_id: int
    step_name: str
    status: str
    message: str
    details: Optional[dict[str, Any]] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskRunLogOut(BaseModel):
    """Row-level error log entry"""
    id: int
    task_id: int
    run_id: int
    row_index: int
    row_data: dict[str, Any]
    errors: list[dict[str, Any]]
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskRunOut(BaseModel):
    """Complete task run with all logs and results"""
    id: int
    task_id: int
    status: str
    records_fetched: int
    records_inserted: int
    records_failed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    execution_logs: list[TaskLogOut] = []
    row_errors: list[TaskRunLogOut] = []
    
    class Config:
        from_attributes = True

class TaskStatsOut(BaseModel):
    """Task execution statistics"""
    task_id: int
    total_runs: int
    successful_runs: int
    failed_runs: int
    success_rate: float  # Percentage 0-100
    total_records_fetched: int
    total_records_inserted: int
    total_records_failed: int
    avg_duration_seconds: float
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
