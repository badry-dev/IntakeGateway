
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import text
from loguru import logger

from app.db.session import SessionLocal
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.services import api_connector, normalizer, mapper, validator
from app.core.logging import set_task_context, clear_task_context


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
            json_body=task.body_json
        )
        
        # Step 4: Extract records using JSONPath
        log_step(db, task_run_id, "EXTRACT_RECORDS", f"Extracting records with path: {task.record_path}")
        
        records = list(normalizer.select_records(response_data, task.record_path))
        task_run.records_fetched = len(records)
        db.commit()
        
        logger.info(f"Extracted {len(records)} records from API response")
        
        if not records:
            task_run.status = TaskStatus.SUCCESS.value
            task_run.completed_at = datetime.now(timezone.utc)
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
        column_specs = []  # TODO: Could be populated from task metadata or column_mapping
        
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
        
        task_run.records_failed = len(invalid_rows)
        db.commit()
        
        # Step 9: Insert valid rows to Oracle
        if valid_rows:
            log_step(db, task_run_id, "INSERT_DB", f"Inserting {len(valid_rows)} rows to {task.dest_table}")
            
            rows_inserted = insert_batch(
                db=db,
                table_name=task.dest_table,
                rows=valid_rows,
                batch_size=task.batch_size
            )
            
            task_run.records_inserted = rows_inserted
            logger.info(f"Successfully inserted {rows_inserted} rows to {task.dest_table}")
        else:
            task_run.records_inserted = 0
            logger.warning("No valid rows to insert")
        
        # Step 10: Update TaskRun status
        if task_run.records_failed > 0 and task_run.records_inserted > 0:
            task_run.status = TaskStatus.PARTIAL_SUCCESS.value
        elif task_run.records_failed > 0:
            task_run.status = TaskStatus.FAILED.value
        else:
            task_run.status = TaskStatus.SUCCESS.value
        
        task_run.completed_at = datetime.now(timezone.utc)
        db.commit()
        
        log_step(db, task_run_id, "COMPLETE", f"Import completed with status {task_run.status}")
        
        return {
            "task_id": task_id,
            "run_id": task_run_id,
            "status": task_run.status,
            "records_fetched": task_run.records_fetched,
            "records_inserted": task_run.records_inserted,
            "records_failed": task_run.records_failed,
        }
        
    except Exception as e:
        logger.error(f"Import failed for task {task_id}: {str(e)}")
        
        # Update TaskRun status to FAILED
        if task_run_id:
            task_run = db.get(TaskRun, task_run_id)
            if task_run:
                task_run.status = TaskStatus.FAILED.value
                task_run.error_message = str(e)
                task_run.completed_at = datetime.now(timezone.utc)
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
