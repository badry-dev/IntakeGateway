
from pydantic import BaseModel, Field
from typing import Any, Optional

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
