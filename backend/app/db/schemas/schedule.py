"""Pydantic schemas for task scheduling"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from croniter import croniter


class ScheduleCreate(BaseModel):
    """Schema for creating a new schedule"""
    cron_expression: str = Field(
        ..., 
        min_length=5,
        max_length=50,
        description="Cron expression (e.g., '0 2 * * *' for daily at 2 AM)",
        examples=["0 * * * *", "0 2 * * *", "0 2 * * 0"]
    )
    is_active: bool = Field(default=True, description="Whether schedule is active")
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression using croniter"""
        v = v.strip()
        if not croniter.is_valid(v):
            raise ValueError(
                f"Invalid cron expression: '{v}'. "
                "Expected format: minute hour day month weekday (e.g., '0 2 * * *')"
            )
        return v


class ScheduleUpdate(BaseModel):
    """Schema for updating a schedule"""
    cron_expression: Optional[str] = Field(
        None,
        min_length=5,
        max_length=50,
        description="Cron expression (e.g., '0 2 * * *')"
    )
    is_active: Optional[bool] = Field(None, description="Whether schedule is active")
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression if provided"""
        if v is None:
            return v
        
        v = v.strip()
        if not croniter.is_valid(v):
            raise ValueError(
                f"Invalid cron expression: '{v}'. "
                "Expected format: minute hour day month weekday (e.g., '0 2 * * *')"
            )
        return v


class ScheduleOut(BaseModel):
    """Schema for schedule response"""
    id: int
    task_id: int
    cron_expression: str
    is_active: bool
    last_run_date: Optional[datetime] = None
    next_run_date: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ScheduleWithTaskName(ScheduleOut):
    """Schedule response with associated task name"""
    task_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class ScheduleListOut(BaseModel):
    """List of schedules with pagination"""
    schedules: list[ScheduleWithTaskName]
    total_count: int
    skip: int
    limit: int
    
    class Config:
        from_attributes = True
