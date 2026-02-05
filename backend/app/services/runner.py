
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DatabaseError
from loguru import logger

from app.db.session import SessionLocal
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.services import api_connector, normalizer, mapper, validator
from app.core.logging import set_task_context, clear_task_context


class RowStatus(str, Enum):
    """Status of individual row processing"""
    INSERTED = "inserted"
    UPDATED = "updated"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class RowResult:
    """Result of processing a single row"""
    status: RowStatus
    record_key: str
    message: str = ""


async def run_import(task_id: int, db: Session = None) -> dict:
    """
    Execute complete data import pipeline for a task
    
    Pipeline flow:
    1. Fetch task configuration from database
    2. Create TaskRun record with RUNNING status
    3. Fetch data from external API
    4. Extract records using JSONPath
    5. Flatten nested structures
    6. Map source fields to destination columns
    7. Validate each row
    8. Insert valid rows to Oracle in batches
    9. Log errors for invalid rows
    10. Update TaskRun with results
    
    Returns:
        Dictionary with execution results
    """
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False
    
    task_run_id = None
    
    try:
        # Set logging context
        set_task_context(task_id=task_id)
        
        # Step 1: Fetch task configuration
        task = db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        if not task.is_active:
            raise ValueError(f"Task {task_id} is not active")
        
        # Step 2: Create TaskRun record
        task_run = TaskRun(
            task_id=task_id,
            status=TaskStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc)
        )
        db.add(task_run)
        db.commit()
        db.refresh(task_run)
        task_run_id = task_run.id
        
        # Update logging context with run_id
        set_task_context(task_id=task_id, run_id=task_run_id)
        
        logger.info(f"Starting import for task {task_id}, run {task_run_id}")
        
        # Step 3: Fetch data from API
        log_step(db, task_run_id, "FETCH_API", f"Fetching from {task.endpoint_path}")
        
        response_data = await api_connector.fetch_json(
            method=task.http_method,
            url=task.endpoint_path,
            headers=task.headers_json,
            params=task.query_params_json,
            json_body=task.body_json,
            auth_type=task.auth_type,
            api_key=task.api_key,
            username=task.username,
            password=task.password,
            oauth_config=task.oauth_config
        )
        
        # Step 4: Extract records using JSONPath
        log_step(db, task_run_id, "EXTRACT_RECORDS", f"Extracting records with path: {task.record_path}")
        
        records = list(normalizer.select_records(response_data, task.record_path))
        task_run.rows_fetched = len(records)
        db.commit()
        
        logger.info(f"Extracted {len(records)} records from API response")
        
        if not records:
            task_run.status = TaskStatus.SUCCESS.value
            task_run.ended_at = datetime.now(timezone.utc)
            db.commit()
            log_step(db, task_run_id, "COMPLETE", "No records to process")
            return {"task_id": task_id, "run_id": task_run_id, "inserted": 0, "errors": 0}
        
        # Step 5: Flatten nested structures
        log_step(db, task_run_id, "FLATTEN", "Flattening nested JSON structures")
        flattened_records = [normalizer.flatten(record) for record in records]
        
        # Step 6: Map source fields to destination columns
        log_step(db, task_run_id, "MAP_COLUMNS", "Mapping source fields to destination columns")
        
        column_mappings = mapper.get_column_mappings(db, task_id)
        
        if column_mappings:
            mapped_records = mapper.map_rows(flattened_records, column_mappings)
        else:
            # If no mappings defined, use flattened records as-is
            mapped_records = flattened_records
            logger.warning(f"No column mappings found for task {task_id}, using direct mapping")
        
        # Step 7: Validate rows
        log_step(db, task_run_id, "VALIDATE", f"Validating {len(mapped_records)} records")
        
        # Build column specs from task configuration (simplified - could be enhanced)
        column_specs = {}  # Empty dict = no validation rules (accept all data as-is)
        
        valid_rows, invalid_rows = validator.validate_rows(mapped_records, column_specs)
        
        logger.info(f"Validation complete: {len(valid_rows)} valid, {len(invalid_rows)} invalid")
        
        # Step 8: Log validation errors
        for idx, invalid_item in enumerate(invalid_rows):
            row = invalid_item["row"]
            errors = invalid_item["errors"]
            for error in errors:
                log_row_error(
                    db=db,
                    task_run_id=task_run_id,
                    row_number=idx,
                    column_name=error.column,
                    error_type=error.error_type,
                    error_message=error.message,
                    source_value=str(error.value) if error.value is not None else None
                )
        
        task_run.error_count = len(invalid_rows)
        db.commit()
        
        # Step 9: Insert/Upsert valid rows to Oracle
        if valid_rows:
            if task.upsert_enabled:
                # Use upsert logic with skip conditions
                log_step(db, task_run_id, "UPSERT_DB", f"Upserting {len(valid_rows)} rows to {task.dest_table}")

                upsert_results = process_rows_with_upsert(
                    db=db,
                    task=task,
                    task_run_id=task_run_id,
                    rows=valid_rows
                )

                task_run.rows_inserted = upsert_results["inserted"]
                task_run.rows_updated = upsert_results["updated"]
                task_run.rows_skipped = upsert_results["skipped"]
                task_run.error_count += upsert_results["errors"]

                logger.info(
                    f"Upsert complete: {upsert_results['inserted']} inserted, "
                    f"{upsert_results['updated']} updated, "
                    f"{upsert_results['skipped']} skipped, "
                    f"{upsert_results['errors']} errors"
                )
            else:
                # Standard insert batch
                log_step(db, task_run_id, "INSERT_DB", f"Inserting {len(valid_rows)} rows to {task.dest_table}")

                rows_inserted = insert_batch(
                    db=db,
                    table_name=task.dest_table,
                    rows=valid_rows,
                    batch_size=task.batch_size
                )

                task_run.rows_inserted = rows_inserted
                logger.info(f"Successfully inserted {rows_inserted} rows to {task.dest_table}")
        else:
            task_run.rows_inserted = 0
            task_run.rows_updated = 0
            task_run.rows_skipped = 0
            logger.warning("No valid rows to insert")

        # Step 10: Update TaskRun status
        total_success = task_run.rows_inserted + task_run.rows_updated
        if task_run.error_count > 0 and total_success > 0:
            task_run.status = TaskStatus.PARTIAL_SUCCESS.value
        elif task_run.error_count > 0:
            task_run.status = TaskStatus.FAILED.value
        else:
            task_run.status = TaskStatus.SUCCESS.value
        
        task_run.ended_at = datetime.now(timezone.utc)
        db.commit()
        
        log_step(db, task_run_id, "COMPLETE", f"Import completed with status {task_run.status}")
        
        return {
            "task_id": task_id,
            "run_id": task_run_id,
            "status": task_run.status,
            "rows_fetched": task_run.rows_fetched,
            "rows_inserted": task_run.rows_inserted,
            "rows_updated": task_run.rows_updated,
            "rows_skipped": task_run.rows_skipped,
            "error_count": task_run.error_count,
        }
        
    except Exception as e:
        logger.error(f"Import failed for task {task_id}: {str(e)}")
        
        # Update TaskRun status to FAILED
        if task_run_id:
            task_run = db.get(TaskRun, task_run_id)
            if task_run:
                task_run.status = TaskStatus.FAILED.value
                task_run.ended_at = datetime.now(timezone.utc)
                db.commit()
                
                log_step(db, task_run_id, "ERROR", f"Fatal error: {str(e)}")
        
        raise
    
    finally:
        # Clear logging context
        clear_task_context()
        if close_db:
            db.close()


def insert_batch(
    db: Session,
    table_name: str,
    rows: list[dict],
    batch_size: int = 500
) -> int:
    """
    Insert rows into Oracle table in batches with transaction handling

    Args:
        db: SQLAlchemy session
        table_name: Target table name
        rows: List of row dictionaries
        batch_size: Number of rows per batch

    Returns:
        Number of rows inserted
    """
    if not rows:
        return 0

    total_inserted = 0

    # Process in batches
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]

        try:
            # Build dynamic INSERT statement
            if batch:
                columns = list(batch[0].keys())
                column_str = ", ".join(columns)
                placeholders = ", ".join([f":{col}" for col in columns])

                insert_sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholders})"

                # Execute batch insert
                db.execute(text(insert_sql), batch)
                db.commit()

                total_inserted += len(batch)
                logger.debug(f"Inserted batch of {len(batch)} rows ({total_inserted}/{len(rows)})")

        except Exception as e:
            logger.error(f"Failed to insert batch: {str(e)}")
            db.rollback()
            raise

    return total_inserted


def process_rows_with_upsert(
    db: Session,
    task: Task,
    task_run_id: int,
    rows: list[dict],
) -> dict:
    """
    Process rows with upsert logic and skip conditions.
    Never stops on individual row errors - logs and continues.

    Args:
        db: SQLAlchemy session
        task: Task configuration with upsert settings
        task_run_id: ID of current run for logging
        rows: List of row dictionaries to process

    Returns:
        Dictionary with processing statistics
    """
    results = {
        "inserted": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
        "error_details": []
    }

    if not rows:
        return results

    upsert_keys = task.upsert_keys or []
    table_name = task.dest_table

    for idx, row in enumerate(rows):
        try:
            result = _process_single_row(
                db=db,
                task=task,
                row=row,
                row_index=idx
            )

            # Update statistics based on result
            if result.status == RowStatus.INSERTED:
                results["inserted"] += 1
            elif result.status == RowStatus.UPDATED:
                results["updated"] += 1
            elif result.status == RowStatus.SKIPPED:
                results["skipped"] += 1
                logger.info(f"Row {idx} skipped: {result.message}")
            elif result.status == RowStatus.ERROR:
                results["errors"] += 1
                results["error_details"].append({
                    "row_index": idx,
                    "record_key": result.record_key,
                    "error": result.message
                })
                # Log to TaskRunLog
                log_row_error(
                    db=db,
                    task_run_id=task_run_id,
                    row_number=idx,
                    column_name="_upsert",
                    error_type="UPSERT_ERROR",
                    error_message=result.message,
                    source_value=result.record_key
                )

        except (IntegrityError, DatabaseError):
            # Let database-related errors propagate; they should be handled upstream
            raise

        except Exception as e:
            # Catch-all for unexpected errors: log and continue to next record (NEVER stop)
            logger.error(f"Unexpected error processing row {idx}: {e}")
            results["errors"] += 1
            results["error_details"].append({
                "row_index": idx,
                "error": str(e)
            })


            continue  # Continue to next row

    return results


def _process_single_row(
    db: Session,
    task: Task,
    row: dict,
    row_index: int
) -> RowResult:
    """
    Process a single row with upsert and skip logic.

    Args:
        db: SQLAlchemy session
        task: Task configuration
        row: Row data dictionary
        row_index: Index of row for logging

    Returns:
        RowResult with status and details
    """
    upsert_keys = task.upsert_keys or []
    record_key = _get_record_key(row, upsert_keys)

    try:
        # If upsert is not enabled, just insert
        if not task.upsert_enabled or not upsert_keys:
            _insert_single_row(db, task.dest_table, row)
            db.commit()
            return RowResult(status=RowStatus.INSERTED, record_key=record_key)

        # Check if record exists
        existing = _find_existing_record(db, task.dest_table, row, upsert_keys)

        if existing:
            # Check skip condition
            if _should_skip(task, existing):
                return RowResult(
                    status=RowStatus.SKIPPED,
                    record_key=record_key,
                    message=f"Skip condition met: {task.skip_column}={task.skip_value}"
                )

            # Update existing record
            _update_existing_row(db, task.dest_table, row, upsert_keys)
            db.commit()
            return RowResult(status=RowStatus.UPDATED, record_key=record_key)
        else:
            # Insert new record
            _insert_single_row(db, task.dest_table, row)
            db.commit()
            return RowResult(status=RowStatus.INSERTED, record_key=record_key)

    except IntegrityError as e:
        # Primary key or unique constraint violation
        db.rollback()
        error_msg = f"Constraint violation: {str(e)[:200]}"
        logger.warning(f"Row {row_index} ({record_key}): {error_msg}")
        return RowResult(
            status=RowStatus.ERROR,
            record_key=record_key,
            message=error_msg
        )

    except DatabaseError as e:
        # Other database errors
        db.rollback()
        error_msg = f"Database error: {str(e)[:200]}"
        logger.error(f"Row {row_index} ({record_key}): {error_msg}")
        return RowResult(
            status=RowStatus.ERROR,
            record_key=record_key,
            message=error_msg
        )


def _get_record_key(row: dict, upsert_keys: list) -> str:
    """Generate a readable key for logging."""
    if upsert_keys:
        return ", ".join(f"{k}={row.get(k)}" for k in upsert_keys)
    return f"row_{id(row)}"


def _find_existing_record(
    db: Session,
    table_name: str,
    row: dict,
    upsert_keys: list
) -> Optional[dict]:
    """Check if a record exists in the database based on upsert keys."""
    if not upsert_keys:
        return None

    where_clauses = " AND ".join([f"{key} = :{key}" for key in upsert_keys])
    params = {key: row.get(key) for key in upsert_keys}

    query = f"SELECT * FROM {table_name} WHERE {where_clauses}"
    result = db.execute(text(query), params).fetchone()

    if result:
        # Convert to dictionary
        return dict(result._mapping)
    return None


def _get_case_insensitive_value(record: dict, column_name: str):
    """
    Retrieve a value from a record using a column name in a case-insensitive way.

    Tries UPPER, lower, then the original column name to match how Oracle
    typically returns column names, while remaining robust to variations.
    """
    if not record or not column_name:
        return None

    for key in (column_name.upper(), column_name.lower(), column_name):
        if key in record:
            return record.get(key)

    return None


def _should_skip(task: Task, existing_record: dict) -> bool:
    """Check if record should be skipped based on skip_column/skip_value."""
    if not task.skip_column or not task.skip_value:
        return False

    current_value = _get_case_insensitive_value(existing_record, task.skip_column)

    if current_value is None:
        return False

    return str(current_value).upper() == str(task.skip_value).upper()


def _insert_single_row(db: Session, table_name: str, row: dict):
    """Insert a single row into the table."""
    columns = list(row.keys())
    column_str = ", ".join(columns)
    placeholders = ", ".join([f":{col}" for col in columns])

    insert_sql = f"INSERT INTO {table_name} ({column_str}) VALUES ({placeholders})"
    db.execute(text(insert_sql), row)


def _update_existing_row(db: Session, table_name: str, row: dict, upsert_keys: list):
    """Update an existing row in the table."""
    update_cols = [col for col in row.keys() if col not in upsert_keys]

    if not update_cols:
        return  # Nothing to update

    set_clause = ", ".join([f"{col} = :{col}" for col in update_cols])
    where_clause = " AND ".join([f"{key} = :{key}" for key in upsert_keys])

    update_sql = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
    db.execute(text(update_sql), row)


def log_step(db: Session, task_run_id: int, step_name: str, message: str, details: dict = None):
    """Log execution step to TaskLog table"""
    log_entry = TaskLog(
        task_run_id=task_run_id,
        step_name=step_name,
        message=message,
        details=details  # Store as JSON dict
    )
    db.add(log_entry)
    db.commit()


def log_row_error(
    db: Session,
    task_run_id: int,
    row_number: int,
    column_name: str,
    error_type: str,
    error_message: str,
    source_value: str = None
):
    """Log row-level validation error to TaskRunLog table"""
    error_log = TaskRunLog(
        task_run_id=task_run_id,
        row_number=row_number,
        column_name=column_name,
        error_type=error_type,
        error_message=error_message,
        source_value=source_value
    )
    db.add(error_log)
    db.commit()
