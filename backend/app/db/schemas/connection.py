"""
Pydantic schemas for database connection configuration.

These schemas handle validation and serialization for the connection management API.
Passwords are excluded from response schemas for security.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ConnectionBase(BaseModel):
    """Base connection fields shared by create/update/response"""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Human-readable connection name"
    )
    db_type: Literal["oracle", "postgresql", "mysql"] = Field(
        default="oracle", description="Database type"
    )
    host: str = Field(..., min_length=1, max_length=500, description="Database host")
    port: int = Field(default=1521, ge=1, le=65535, description="Database port")
    username: str = Field(..., min_length=1, max_length=200, description="Database username")
    service_name: str | None = Field(None, max_length=100, description="Oracle service name")
    database: str | None = Field(
        None, max_length=200, description="Database name (PostgreSQL/MySQL)"
    )
    connection_options: dict | None = Field(None, description="Additional driver options")

    @field_validator("service_name")
    @classmethod
    def validate_service_name(cls, v: str | None, info) -> str | None:
        """Require service_name for Oracle connections"""
        db_type = info.data.get("db_type", "oracle")
        if db_type == "oracle" and not v:
            raise ValueError("service_name is required for Oracle connections")
        return v

    @field_validator("database")
    @classmethod
    def validate_database(cls, v: str | None, info) -> str | None:
        """Require database for PostgreSQL/MySQL connections"""
        db_type = info.data.get("db_type", "oracle")
        if db_type in ("postgresql", "mysql") and not v:
            raise ValueError(f"database is required for {db_type} connections")
        return v


class ConnectionCreate(ConnectionBase):
    """Schema for creating a new connection - includes password"""

    password: str = Field(..., min_length=1, description="Database password")


class ConnectionUpdate(BaseModel):
    """Schema for updating a connection - all fields optional"""

    name: str | None = Field(None, min_length=1, max_length=100)
    db_type: Literal["oracle", "postgresql", "mysql"] | None = None
    host: str | None = Field(None, min_length=1, max_length=500)
    port: int | None = Field(None, ge=1, le=65535)
    username: str | None = Field(None, min_length=1, max_length=200)
    password: str | None = Field(None, min_length=1, description="Only update if provided")
    service_name: str | None = Field(None, max_length=100)
    database: str | None = Field(None, max_length=200)
    connection_options: dict | None = None


class ConnectionOut(BaseModel):
    """Response schema - excludes password for security"""

    id: str
    name: str
    db_type: str
    host: str
    port: int
    username: str
    service_name: str | None = None
    database: str | None = None
    connection_options: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionListOut(BaseModel):
    """List of saved connections"""

    connections: list[ConnectionOut]
    total_count: int


class ConnectionTestRequest(BaseModel):
    """Request for testing connection without saving"""

    db_type: Literal["oracle", "postgresql", "mysql"] = "oracle"
    host: str = Field(..., min_length=1)
    port: int = Field(default=1521, ge=1, le=65535)
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)
    service_name: str | None = None
    database: str | None = None


class ConnectionTestResult(BaseModel):
    """Result of connection test"""

    success: bool
    message: str
    latency_ms: int | None = None
    server_version: str | None = None
