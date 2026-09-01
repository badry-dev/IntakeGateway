"""API routes for column mapping operations.

Endpoints:
- GET /api/v1/tasks/{task_id}/mappings - List all mappings for a task
- POST /api/v1/tasks/{task_id}/mappings - Create new mappings (bulk)
- PUT /api/v1/mappings/{mapping_id} - Update a mapping
- DELETE /api/v1/mappings/{mapping_id} - Delete a mapping
- POST /api/v1/tasks/{task_id}/preview-fields - Fetch sample API response
- GET /api/v1/oracle/tables/{table_name}/columns - Query Oracle metadata
"""

import base64
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.url_guard import SSRFBlockedError, validate_url_async
from app.db.models.column_mapping import ColumnMapping
from app.db.models.task import Task
from app.db.schemas.column_mapping import (
    BulkMappingCreate,
    ColumnMappingOut,
    ColumnMappingUpdate,
    FieldPreview,
    FieldsPreviewResponse,
    OracleColumnsResponse,
    PreviewFieldsRequest,
    SanitizedFieldPreview,
    StandaloneFieldsPreviewResponse,
    TransformSuggestionsResponse,
)
from app.db.session import SessionLocal
from app.services.api_connector import fetch_sample_response, get_record_type_info
from app.services.connection_pool import get_session as get_destination_session
from app.services.oracle_metadata import get_table_columns
from app.services.transform_suggester import suggest_transforms

router = APIRouter()
oracle_router = APIRouter()
logger = logging.getLogger(__name__)


def _headers_with_plaintext_preview_auth(request: PreviewFieldsRequest) -> dict:
    """Apply wizard-time auth values to standalone preview headers.

    Standalone preview runs before a Task is saved, so bearer/api-key/basic
    secrets are still plaintext form values rather than encrypted database
    values. The shared task runner auth helper expects encrypted fields, so the
    preview route builds those headers directly.
    """
    headers = dict(request.headers or {})
    auth_type = request.auth_type or "none"

    if auth_type == "bearer" and request.api_key:
        headers["Authorization"] = f"Bearer {request.api_key}"
    elif auth_type == "api_key" and request.api_key:
        header_name = (request.oauth_config or {}).get("api_key_header", "X-API-Key")
        headers[header_name] = request.api_key
    elif auth_type == "basic" and request.username and request.password:
        credentials = f"{request.username}:{request.password}".encode()
        headers["Authorization"] = f"Basic {base64.b64encode(credentials).decode()}"
    elif auth_type == "oauth":
        token = (request.oauth_config or {}).get("access_token")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        else:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Standalone sample fetch supports OAuth only when a static access token "
                    "is provided. Save the task before previewing client_credentials or "
                    "refresh_token OAuth flows."
                ),
            )

    return headers


def get_db():
    """Dependency: Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# LIST MAPPINGS
# ============================================================================


@router.get("/{task_id}/mappings", response_model=list[ColumnMappingOut])
def list_mappings(
    task_id: int,
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=500, description="Number of records to return"),
    is_active: bool = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
):
    """
    List all column mappings for a task.

    Args:
        task_id: ID of the task
        skip: Pagination offset
        limit: Pagination limit
        is_active: Filter by active/inactive status (optional)

    Returns:
        List of column mappings

    Raises:
        404: Task not found
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Build query
    query = db.query(ColumnMapping).filter(ColumnMapping.task_id == task_id)

    if is_active is not None:
        query = query.filter(ColumnMapping.is_active == is_active)

    # Execute query with pagination
    total = query.count()
    mappings = query.order_by(ColumnMapping.id).offset(skip).limit(limit).all()

    logger.info(f"Listed {len(mappings)} mappings for task {task_id} (total: {total})")
    return mappings


# ============================================================================
# CREATE MAPPINGS (BULK)
# ============================================================================


@router.post("/{task_id}/mappings", response_model=list[ColumnMappingOut], status_code=201)
def create_mappings(task_id: int, payload: BulkMappingCreate, db: Session = Depends(get_db)):
    """
    Create multiple column mappings for a task (bulk operation).

    Args:
        task_id: ID of the task
        payload: Bulk mapping creation request with list of mappings

    Returns:
        List of created mappings

    Raises:
        404: Task not found
        400: Duplicate mapping or validation error
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if not payload.mappings:
        raise HTTPException(status_code=400, detail="At least one mapping is required")

    created_mappings = []

    for mapping_data in payload.mappings:
        # Check for duplicate source_field
        existing = (
            db.query(ColumnMapping)
            .filter(
                ColumnMapping.task_id == task_id,
                ColumnMapping.source_field == mapping_data.source_field,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Mapping for field '{mapping_data.source_field}' already exists for this task",
            )

        # Create mapping
        mapping = ColumnMapping(
            task_id=task_id,
            source_field=mapping_data.source_field,
            dest_column=mapping_data.dest_column,
            transform_rules=json.dumps(mapping_data.transform_rules)
            if mapping_data.transform_rules
            else None,
            is_active=mapping_data.is_active,
        )

        db.add(mapping)
        created_mappings.append(mapping)

    # Commit all at once
    db.commit()

    # Refresh all objects to get created_at and updated_at
    for mapping in created_mappings:
        db.refresh(mapping)

    logger.info(f"Created {len(created_mappings)} mappings for task {task_id}")
    return created_mappings


# ============================================================================
# UPDATE MAPPING
# ============================================================================


@router.put("/{mapping_id}", response_model=ColumnMappingOut)
def update_mapping(mapping_id: int, payload: ColumnMappingUpdate, db: Session = Depends(get_db)):
    """
    Update an existing column mapping.

    Args:
        mapping_id: ID of the mapping to update
        payload: Update data (all fields optional)

    Returns:
        Updated mapping

    Raises:
        404: Mapping not found
        400: Duplicate field mapping or validation error
    """
    mapping = db.query(ColumnMapping).filter(ColumnMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    # If updating source_field, check for duplicates
    if payload.source_field and payload.source_field != mapping.source_field:
        existing = (
            db.query(ColumnMapping)
            .filter(
                ColumnMapping.task_id == mapping.task_id,
                ColumnMapping.source_field == payload.source_field,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Mapping for field '{payload.source_field}' already exists for this task",
            )

    # Update only provided fields
    update_data = payload.model_dump(exclude_unset=True)

    # Handle transform_rules JSON serialization
    if "transform_rules" in update_data:
        transform_rules = update_data["transform_rules"]
        update_data["transform_rules"] = json.dumps(transform_rules) if transform_rules else None

    for key, value in update_data.items():
        setattr(mapping, key, value)

    db.commit()
    db.refresh(mapping)

    logger.info(f"Updated mapping {mapping_id}")
    return mapping


# ============================================================================
# DELETE MAPPING
# ============================================================================


@router.delete("/{mapping_id}", status_code=204)
def delete_mapping(mapping_id: int, db: Session = Depends(get_db)):
    """
    Delete a column mapping.

    Args:
        mapping_id: ID of the mapping to delete

    Raises:
        404: Mapping not found
    """
    mapping = db.query(ColumnMapping).filter(ColumnMapping.id == mapping_id).first()
    if not mapping:
        raise HTTPException(status_code=404, detail="Mapping not found")

    db.delete(mapping)
    db.commit()

    logger.info(f"Deleted mapping {mapping_id}")
    return None


# ============================================================================
# PREVIEW FIELDS FROM SAMPLE RESPONSE
# ============================================================================


@router.post("/{task_id}/preview-fields", response_model=FieldsPreviewResponse)
async def preview_fields(
    task_id: int,
    sample_json: dict = None,
    use_auto_fetch: bool = Query(
        False, description="Whether to auto-fetch from API or use manual sample_json"
    ),
    db: Session = Depends(get_db),
):
    """
    Preview available fields from a sample API response.

    Supports two modes:
    1. Auto-fetch: Makes a test API call to fetch real sample response
    2. Manual: Uses provided sample_json (user pastes JSON)

    Args:
        task_id: ID of the task
        sample_json: Manual sample JSON (required if use_auto_fetch=False)
        use_auto_fetch: Whether to auto-fetch from configured API endpoint

    Returns:
        FieldsPreviewResponse with available fields and flattened structure

    Raises:
        404: Task not found
        400: Invalid JSON or API fetch failed
    """
    # Verify task exists
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Debug logging for task authentication
    logger.info(
        f"Task {task_id} auth config: auth_type={task.auth_type}, has_api_key={bool(task.api_key)}, has_username={bool(task.username)}"
    )

    try:
        if use_auto_fetch:
            # Auto-fetch mode: make test API call
            raw_response = await fetch_sample_response(
                method=task.http_method,
                url=task.endpoint_path,
                headers=task.headers_json,
                params=task.query_params_json,
                json_body=task.body_json,
                record_path=task.record_path,
                auth_type=task.auth_type,
                api_key=task.api_key,
                username=task.username,
                password=task.password,
                oauth_config=task.oauth_config,
                task=task,
                db=db,
            )
        else:
            if not sample_json:
                raise HTTPException(
                    status_code=400,
                    detail="sample_json is required when use_auto_fetch=False",
                )
            raw_response = sample_json

        # Get field information (flatten and infer types)
        flattened_data = get_record_type_info(raw_response, task.record_path)

        # Convert dict to list of FieldPreview objects
        fields_info = []
        for field_name, field_info in flattened_data.items():
            fields_info.append(
                FieldPreview(
                    field_name=field_name,
                    field_type=field_info.get("field_type", "string"),
                    sample_value=field_info.get("sample_value"),
                    is_nested=field_info.get("parent_path") is not None,
                    parent_path=field_info.get("parent_path"),
                )
            )

        logger.info(f"Generated field preview for task {task_id}: {len(fields_info)} fields")

        return FieldsPreviewResponse(
            fields=fields_info,
            sample_response=raw_response,
            flattened_response=flattened_data,
            field_count=len(fields_info),
        )

    except HTTPException:
        # Re-raise deliberate HTTP errors instead of rewriting them to 400.
        raise
    except SSRFBlockedError as e:
        # Raised by the fetch-time re-validation inside fetch_json. It
        # subclasses ValueError, so it must be handled before that branch or
        # it surfaces as a misleading 400 "Invalid JSON".
        logger.warning(f"SSRF guard rejected preview fetch: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.warning(f"Invalid JSON for task {task_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching preview for task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch/parse sample response: {str(e)}"
        )


# ============================================================================
# QUERY ORACLE TABLE COLUMNS
# ============================================================================


@oracle_router.get("/oracle/tables/{table_name}/columns", response_model=OracleColumnsResponse)
def get_columns(
    table_name: str,
    connection_id: str = Query(..., min_length=1, description="Required destination connection ID"),
):
    """
    Query Oracle database for table column information.

    Uses Oracle USER_TAB_COLUMNS system view to get column names, types, and constraints.
    Supports tables owned by other users that the current user has access to.

    Args:
        table_name: Name of the Oracle table (case-insensitive)

    Returns:
        OracleColumnsResponse with list of columns and metadata

    Raises:
        404: Table not found
        400: Permission denied or database error
    """
    try:
        destination_db = None
        try:
            destination_db = get_destination_session(connection_id)
            columns = get_table_columns(destination_db, table_name)
        finally:
            if destination_db is not None:
                destination_db.close()

        # If we get an empty list, return 404 with helpful message
        if not columns:
            logger.warning(f"No columns found for table {table_name}")
            raise HTTPException(
                status_code=404,
                detail=f"Table '{table_name}' not found. Make sure the table name is correct and you have permission to access it.",
            )

        logger.info(f"Retrieved {len(columns)} columns from table {table_name}")

        return OracleColumnsResponse(
            table_name=table_name, columns=columns, column_count=len(columns)
        )

    except PermissionError as e:
        logger.warning(f"Permission denied querying table {table_name}: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"Permission denied: Insufficient privileges to query table '{table_name}'",
        )
    except Exception as e:
        logger.error(f"Error querying table {table_name}: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Database error: {str(e)}")


# ============================================================================
# SUGGEST TRANSFORMS
# ============================================================================

# ============================================================================
# PREVIEW FIELDS (STANDALONE - FOR WIZARD)
# ============================================================================


@oracle_router.post(
    "/preview-fields-standalone",
    response_model=FieldsPreviewResponse | StandaloneFieldsPreviewResponse,
)
async def preview_fields_standalone(request: PreviewFieldsRequest):
    """
    Preview available fields from a sample API response (standalone - no task required).

    Useful for TaskWizard mapping step before task creation.

    Supports two modes:
    1. Auto-fetch: Makes a test API call with provided parameters. The URL is
       validated against the SSRF guard, and the response returns ONLY derived
       field metadata (no sample values / raw response are echoed back).
    2. Manual: Uses provided sample_json (user pastes JSON). The user-supplied
       JSON is echoed back as before.

    Args:
        request: PreviewFieldsRequest with all parameters

    Returns:
        FieldsPreviewResponse (manual mode) or StandaloneFieldsPreviewResponse
        (auto-fetch mode)

    Raises:
        400: Invalid JSON or API fetch failed
        403: URL blocked by SSRF guard
    """
    try:
        if request.use_auto_fetch:
            if not request.url:
                raise HTTPException(
                    status_code=400, detail="url parameter required for auto-fetch mode"
                )

            # SSRF guard (C4): reject private/loopback/link-local targets.
            try:
                # Async variant: DNS resolution must not block the event loop.
                await validate_url_async(request.url)
            except SSRFBlockedError as e:
                logger.warning(f"SSRF guard rejected standalone preview URL: {e}")
                raise HTTPException(status_code=403, detail=str(e))

            logger.info(f"Auto-fetching from {request.method} {request.url}")
            raw_response = await fetch_sample_response(
                method=request.method,
                url=request.url,
                headers=_headers_with_plaintext_preview_auth(request),
                params=request.params,
                json_body=request.json_body,
                record_path=request.record_path,
                auth_type="none",
            )

            sample_record = raw_response
            if isinstance(raw_response, list):
                if not raw_response:
                    raise ValueError("Cannot process empty list")
                sample_record = raw_response[0]

            flattened_data = get_record_type_info(sample_record, request.record_path)

            # Auto-fetch echoes NO source values — only derived metadata.
            fields_info = [
                SanitizedFieldPreview(
                    field_name=field_name,
                    field_type=field_info.get("field_type", "string"),
                    is_nested=field_info.get("parent_path") is not None,
                    parent_path=field_info.get("parent_path"),
                )
                for field_name, field_info in flattened_data.items()
            ]

            logger.info(f"Generated field preview (standalone): {len(fields_info)} fields")

            return StandaloneFieldsPreviewResponse(
                fields=fields_info,
                field_count=len(fields_info),
            )

        if not request.sample_json:
            raise HTTPException(
                status_code=400,
                detail="sample_json is required when use_auto_fetch=False",
            )
        raw_response = request.sample_json

        # Ensure we have a dict for processing (extract first record if list)
        sample_record = raw_response
        if isinstance(raw_response, list):
            if not raw_response:
                raise ValueError("Cannot process empty list")
            sample_record = raw_response[0]

        # Get field information (flatten and infer types)
        # Returns dict: {"field.name": {"field_type": "...", "sample_value": ..., ...}, ...}
        flattened_data = get_record_type_info(sample_record, request.record_path)

        # Convert dict to list of FieldPreview objects
        fields_info = []
        for field_name, field_info in flattened_data.items():
            fields_info.append(
                FieldPreview(
                    field_name=field_name,
                    field_type=field_info.get("field_type", "string"),
                    sample_value=field_info.get("sample_value"),
                    is_nested=field_info.get("parent_path") is not None,
                    parent_path=field_info.get("parent_path"),
                )
            )

        logger.info(f"Generated field preview (standalone): {len(fields_info)} fields")

        return FieldsPreviewResponse(
            fields=fields_info,
            sample_response=sample_record,  # Use the first record dict, not the full response
            flattened_response=flattened_data,
            field_count=len(fields_info),
        )

    except HTTPException:
        # Re-raise deliberate HTTP errors (400 missing sample_json, 403 SSRF
        # block) instead of letting the broad handler rewrite them to 400.
        raise
    except SSRFBlockedError as e:
        # Raised by the fetch-time re-validation inside fetch_json. It
        # subclasses ValueError, so it must be handled before that branch or
        # it surfaces as a misleading 400 "Invalid JSON".
        logger.warning(f"SSRF guard rejected preview fetch: {e}")
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.warning(f"Invalid JSON: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error fetching preview (standalone): {str(e)}")
        raise HTTPException(
            status_code=400, detail=f"Failed to fetch/parse sample response: {str(e)}"
        )


@oracle_router.post("/suggest-transforms", response_model=TransformSuggestionsResponse)
def suggest_transforms_endpoint(
    source_type: str = Query(
        ...,
        description="Source field type (string, number, boolean, array, object, null)",
    ),
    dest_type: str = Query(
        ...,
        description="Destination column type (VARCHAR2, NUMBER, DATE, TIMESTAMP, etc)",
    ),
):
    """
    Get recommended transforms for a source-destination type pair.

    Args:
        source_type: Type of the API response field
        dest_type: Type of the database column

    Returns:
        TransformSuggestionsResponse with recommended transforms

    Raises:
        400: Invalid type pair
    """
    try:
        suggestions = suggest_transforms(source_type, dest_type)

        logger.info(
            f"Generated {len(suggestions.suggestions)} suggestions for {source_type} → {dest_type}"
        )

        return suggestions

    except ValueError as e:
        logger.warning(f"Invalid type pair: {source_type} → {dest_type}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error suggesting transforms: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error generating suggestions: {str(e)}")
