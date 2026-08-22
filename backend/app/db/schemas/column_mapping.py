"""Pydantic schemas for Column Mapping operations."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ColumnMappingCreate(BaseModel):
    """Input schema for creating a new column mapping."""

    source_field: str = Field(
        ...,
        description="API response field name (supports dot notation for nested fields)",
    )
    dest_column: str = Field(..., description="Oracle database column name")
    transform_rules: list[str] | None = Field(
        None,
        description="List of transforms to apply: trim, upper, lower, to_int, to_float, to_bool, to_timestamp, to_date, format_date",
    )
    is_active: bool = Field(default=True, description="Enable/disable this mapping")


class ColumnMappingUpdate(BaseModel):
    """Input schema for updating an existing column mapping."""

    source_field: str | None = Field(None, description="API response field name")
    dest_column: str | None = Field(None, description="Oracle database column name")
    transform_rules: list[str] | None = Field(None, description="List of transforms")
    is_active: bool | None = Field(None, description="Enable/disable this mapping")


class ColumnMappingOut(BaseModel):
    """Output schema for column mapping responses."""

    id: int
    task_id: int
    source_field: str
    dest_column: str
    transform_rules: list[str] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @model_validator(mode="before")
    @classmethod
    def parse_json_fields(cls, data: Any) -> Any:
        """Parse JSON string fields from database."""
        # Handle both dict and SQLAlchemy model objects
        if hasattr(data, "__dict__"):
            # SQLAlchemy model - convert to dict for parsing
            data_dict = {
                key: getattr(data, key)
                for key in [
                    "id",
                    "task_id",
                    "source_field",
                    "dest_column",
                    "transform_rules",
                    "is_active",
                    "created_at",
                    "updated_at",
                ]
            }
            data = data_dict

        if isinstance(data, dict):
            # Parse transform_rules if it's a string
            if "transform_rules" in data and isinstance(data["transform_rules"], str):
                try:
                    parsed = json.loads(data["transform_rules"])
                    data["transform_rules"] = parsed if isinstance(parsed, list) else None
                except (json.JSONDecodeError, TypeError):
                    data["transform_rules"] = None
        return data


class BulkMappingCreate(BaseModel):
    """Input schema for bulk creating multiple column mappings."""

    mappings: list[ColumnMappingCreate] = Field(..., description="List of mappings to create")


class FieldPreview(BaseModel):
    """Schema for field preview from sample API response."""

    field_name: str = Field(
        ..., description="Full dot notation field name (e.g., user.address.city)"
    )
    field_type: str = Field(
        ..., description="Inferred type: string, number, boolean, null, array, object"
    )
    sample_value: Any | None = Field(None, description="Sample value from the response")
    is_nested: bool = Field(default=False, description="Whether this is a nested field")
    parent_path: str | None = Field(None, description="Parent path for nested fields")


class PreviewFieldsRequest(BaseModel):
    """Request schema for preview-fields-standalone endpoint."""

    use_auto_fetch: bool = Field(
        False, description="Whether to auto-fetch from API or use manual sample_json"
    )
    sample_json: dict | None = Field(
        None, description="Manual sample JSON (required if use_auto_fetch=False)"
    )
    method: str = Field("GET", description="HTTP method for auto-fetch")
    url: str | None = Field(
        None, description="API URL for auto-fetch (required if use_auto_fetch=True)"
    )
    headers: dict | None = Field(None, description="HTTP headers for auto-fetch")
    params: dict | None = Field(None, description="Query parameters for auto-fetch")
    json_body: dict | None = Field(None, description="Request body for auto-fetch")
    record_path: str | None = Field(None, description="JSONPath to extract records")
    # Authentication fields (Phase 7)
    auth_type: str | None = Field(
        None,
        description="Authentication type: 'none', 'bearer', 'api_key', 'basic', 'oauth'",
    )
    api_key: str | None = Field(None, description="API key (encrypted)")
    username: str | None = Field(None, description="Username for Basic auth")
    password: str | None = Field(None, description="Password for Basic auth (encrypted)")
    oauth_config: dict | None = Field(None, description="OAuth configuration")


class FieldsPreviewResponse(BaseModel):
    """Response schema for field preview endpoint."""

    fields: list[FieldPreview] = Field(..., description="Available fields from the sample response")
    sample_response: dict = Field(
        ..., description="The raw sample response (for tree view construction)"
    )
    flattened_response: dict = Field(..., description="Flattened version of the sample response")
    field_count: int = Field(..., description="Total number of fields")


class SanitizedFieldPreview(BaseModel):
    """Field metadata without source values (SSRF-safe auto-fetch responses).

    Auto-fetched sample values echo third-party data to unauthenticated
    callers; only derived metadata is returned.
    """

    field_name: str = Field(..., description="Full dot notation field name")
    field_type: str = Field(..., description="Inferred type")
    is_nested: bool = Field(default=False, description="Whether this is a nested field")
    parent_path: str | None = Field(None, description="Parent path for nested fields")


class StandaloneFieldsPreviewResponse(BaseModel):
    """Response for standalone preview auto-fetch: metadata only, no samples."""

    fields: list[SanitizedFieldPreview] = Field(
        ..., description="Available fields (no sample values)"
    )
    field_count: int = Field(..., description="Total number of fields")


class OracleColumn(BaseModel):
    """Schema for Oracle table column information."""

    column_name: str = Field(..., description="Column name in Oracle table")
    data_type: str = Field(
        ..., description="Oracle data type (e.g., VARCHAR2, NUMBER, DATE, TIMESTAMP)"
    )
    nullable: bool = Field(..., description="Whether column allows NULL")
    max_length: int | None = Field(None, description="Max length for string types")


class OracleColumnsResponse(BaseModel):
    """Response schema for Oracle columns endpoint."""

    table_name: str = Field(..., description="Table name")
    columns: list[OracleColumn] = Field(..., description="List of columns in the table")
    column_count: int = Field(..., description="Total number of columns")


class TransformSuggestion(BaseModel):
    """Schema for transform suggestion."""

    transform_name: str = Field(..., description="Name of suggested transform")
    reason: str = Field(..., description="Why this transform is suggested")
    priority: str = Field("medium", description="Priority level: high, medium, low")


class TransformSuggestionsResponse(BaseModel):
    """Response schema for transform suggestions."""

    source_type: str = Field(..., description="Source field type")
    dest_type: str = Field(..., description="Destination column type")
    suggestions: list[TransformSuggestion] = Field(
        ..., description="List of recommended transforms"
    )
    requires_transform: bool = Field(
        ..., description="Whether a transform is necessary for compatibility"
    )
    warning_message: str | None = Field(None, description="Warning if types are incompatible")


class MappingTemplate(BaseModel):
    """Schema for mapping template (for localStorage on frontend, but included for API consistency)."""

    template_name: str = Field(..., description="User-defined template name")
    mappings: list[ColumnMappingCreate] = Field(
        ..., description="List of mappings in this template"
    )
    description: str | None = Field(None, description="Template description")
    created_at: datetime | None = None
