
import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, DatabaseError
from loguru import logger


# Cursor identifiers go directly into URL query params; whitelist them strictly.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")


def _redact_cursor(value):
    """Same redaction policy as workers.tasks._redact_cursor — see that
    function for rationale. Duplicated here to avoid a circular import
    (runner imported by worker)."""
    if value is None:
        return "<none>"
    s = str(value)
    if not s:
        return "<empty>"
    digest = hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()[:8]
    return f"<len={len(s)} sha256={digest}>"

from app.db.session import SessionLocal
from app.db.models.task import Task
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_log import TaskLog
from app.db.models.task_run_log import TaskRunLog
from app.services import api_connector, normalizer, mapper, validator
from app.services.connection_pool import get_session as get_destination_session
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


async def run_import(
    task_id: int,
    db: Session = None,
    destination_db: Session = None,
    cursor_override_start: Optional[str] = None,
    cursor_override_end: Optional[str] = None,
    is_backfill: bool = False,
    replay_of_run_id: Optional[int] = None,
    force_replay: bool = False,
) -> dict:
    """
    Execute complete data import pipeline for a task.

    Pipeline flow:
    1. Fetch task configuration from database
    2. Resolve cursor window (override > task.cursor_last_value > task.cursor_initial_value)
    3. Create TaskRun record with RUNNING status (tagging is_backfill / is_replay)
    4. Fetch data from external API (cursor injected as query param if configured)
    5. Extract records using JSONPath; flatten and map; validate
    6. Insert valid rows to the destination DB
    7. Compute cursor_end and persist on TaskRun
    8. For non-backfill, non-replay successful runs: advance task.cursor_last_value

    Replay semantics: if `replay_of_run_id` is set, the prior run's cursor window
    is reused (deduped via existing upsert logic). Replay is refused when the
    task has `upsert_enabled=False` and `force_replay=False`, since non-upsert
    replays would re-insert duplicates.
    """
    if db is None:
        db = SessionLocal()
        close_db = True
    else:
        close_db = False

    close_destination_db = False

    task_run_id = None
    is_replay = replay_of_run_id is not None

    try:
        # Set logging context
        set_task_context(task_id=task_id)

        # Step 1: Fetch task configuration
        task = db.get(Task, task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not task.is_active:
            raise ValueError(f"Task {task_id} is not active")

        if not task.connection_id:
            raise ValueError(f"Task {task_id} requires a destination connection")

        # Replay safety: refuse replays for non-upsert tasks unless forced.
        # Upsert is what makes a replay safely idempotent — without it we'd
        # double-insert on every replay.
        if is_replay and not task.upsert_enabled and not force_replay:
            raise ValueError(
                f"Replay refused: task {task_id} has upsert_enabled=False. "
                "Replays require upsert to be safely idempotent. "
                "Pass force=true to override (will likely insert duplicates)."
            )

        # Resolve cursor window. Override has highest precedence (used by backfill /
        # replay endpoints); otherwise fall back to the persisted watermark, then
        # to the configured initial value, then to None (cursor disabled).
        # Only treat string values as configured cursor identifiers — older tests
        # use MagicMock fixtures that would otherwise fail the regex check.
        cursor_field = task.cursor_field if isinstance(task.cursor_field, str) else None
        cursor_param_name = (
            task.cursor_param_name if isinstance(task.cursor_param_name, str) else None
        )
        if cursor_param_name and not _SAFE_IDENTIFIER_RE.match(cursor_param_name):
            raise ValueError(
                f"cursor_param_name {cursor_param_name!r} is invalid; "
                "must match ^[A-Za-z_][A-Za-z0-9_]{0,99}$"
            )
        if cursor_field and not _SAFE_IDENTIFIER_RE.match(cursor_field):
            raise ValueError(
                f"cursor_field {cursor_field!r} is invalid; "
                "must match ^[A-Za-z_][A-Za-z0-9_]{0,99}$"
            )

        if cursor_override_start is not None:
            cursor_start_value = cursor_override_start
        elif cursor_field:
            cursor_start_value = task.cursor_last_value or task.cursor_initial_value
        else:
            cursor_start_value = None

        # Step 2: Create TaskRun record
        task_run = TaskRun(
            task_id=task_id,
            status=TaskStatus.RUNNING.value,
            started_at=datetime.now(timezone.utc),
            cursor_start=cursor_start_value,
            is_backfill=is_backfill,
            is_replay=is_replay,
            replay_of_run_id=replay_of_run_id,
        )
        db.add(task_run)
        db.commit()
        db.refresh(task_run)
        task_run_id = task_run.id

        # Update logging context with run_id
        set_task_context(task_id=task_id, run_id=task_run_id)

        logger.info(
            f"Starting import for task {task_id}, run {task_run_id} "
            f"(backfill={is_backfill}, replay={is_replay}, "
            f"cursor_start={_redact_cursor(cursor_start_value)}, "
            f"cursor_end={_redact_cursor(cursor_override_end)})"
        )

        # Inject cursor bounds into query params if configured. We copy
        # task.query_params_json rather than mutating it so the persisted task
        # config is untouched. The upper-bound is exposed via a derived
        # `<cursor_param_name>_to` convention so backfills and replays actually
        # constrain the upstream fetch (otherwise a "fixed window" backfill
        # would silently fetch beyond the requested end).
        request_params = dict(task.query_params_json or {})
        if cursor_param_name:
            if cursor_start_value is not None:
                request_params[cursor_param_name] = cursor_start_value
            if cursor_override_end is not None:
                end_param = f"{cursor_param_name}_to"
                # The base param already passed the safe-identifier whitelist;
                # the derived `_to` suffix preserves it. Re-validate defensively.
                if not _SAFE_IDENTIFIER_RE.match(end_param):
                    raise ValueError(
                        f"Derived cursor end param name {end_param!r} is invalid"
                    )
                request_params[end_param] = cursor_override_end

        # Step 3: Fetch data from API (with auth resolution + retries + 429 handling)
        log_step(db, task_run_id, "FETCH_API", f"Fetching from {task.endpoint_path}")

        response_data = await api_connector.fetch_with_auth(
            task=task,
            db=db,
            method=task.http_method,
            url=task.endpoint_path,
            headers=task.headers_json,
            params=request_params,
            json_body=task.body_json,
        )
        
        # Step 4: Extract records using JSONPath
        log_step(db, task_run_id, "EXTRACT_RECORDS", f"Extracting records with path: {task.record_path}")
        
        records = list(normalizer.select_records(response_data, task.record_path))
        task_run.rows_fetched = len(records)
        db.commit()
        
        logger.info(f"Extracted {len(records)} records from API response")
        
        if not records:
            # Empty fetch is still a successful run for cursor purposes.
            # We MUST persist cursor_end (and is_backfill / is_replay) here, or
            # backfill / replay history loses its requested upper bound — and
            # a later replay of this run reads prior.cursor_end as None,
            # silently dropping the fixed-window semantics. Match the metadata
            # shape returned by the non-empty success path.
            task_run.status = TaskStatus.SUCCESS.value
            task_run.cursor_end = cursor_override_end
            task_run.ended_at = datetime.now(timezone.utc)
            # Watermark advancement on empty windows: skip. With zero rows we
            # have no observed source-side max, and silently advancing to
            # cursor_override_end would create off-by-one drift between what
            # the upstream actually emitted and what we record.
            db.commit()
            log_step(db, task_run_id, "COMPLETE", "No records to process")
            return {
                "task_id": task_id,
                "run_id": task_run_id,
                "status": task_run.status,
                "rows_fetched": 0,
                "rows_inserted": 0,
                "rows_updated": 0,
                "rows_skipped": 0,
                "error_count": 0,
                "cursor_start": task_run.cursor_start,
                "cursor_end": task_run.cursor_end,
                "is_backfill": task_run.is_backfill,
                "is_replay": task_run.is_replay,
                "replay_of_run_id": task_run.replay_of_run_id,
            }
        
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
        
        # Step 9: Insert/Upsert valid rows to the configured destination database
        if valid_rows:
            log_step(db, task_run_id, "CONNECT_DESTINATION", "Opening destination database session")

            if destination_db is None:
                destination_db = get_destination_session(task.connection_id)
                close_destination_db = True

            if task.upsert_enabled:
                # Use upsert logic with skip conditions
                log_step(db, task_run_id, "UPSERT_DB", f"Upserting {len(valid_rows)} rows to {task.dest_table}")

                upsert_results = process_rows_with_upsert(
                    db=destination_db,
                    task=task,
                    task_run_id=task_run_id,
                    app_db=db,
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
                    db=destination_db,
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

        # Cursor advancement (P0-C):
        # Cursor bookkeeping splits into two distinct values with different
        # safety requirements:
        #
        #   task_run.cursor_end          — the upper bound of THIS run's window,
        #                                  used by replay to reconstruct the
        #                                  same fetch. Must reflect what the
        #                                  upstream actually returned, including
        #                                  rows that later failed validation or
        #                                  DB write — replay needs to see those
        #                                  again.
        #
        #   task.cursor_last_value       — the high-water mark used to compute
        #                                  the NEXT incremental run's start.
        #                                  Advancing past a row that did NOT
        #                                  land would skip it forever, so we
        #                                  only advance on full SUCCESS (zero
        #                                  errors at any pipeline stage).
        #                                  PARTIAL_SUCCESS persists cursor_end
        #                                  on the run row but holds the
        #                                  watermark steady.
        #
        # We prefer pre-mapping source records (flattened_records) when reading
        # cursor_field because column mapping renames keys to destination
        # columns and the field name typically won't survive.

        def _max_cursor(rows: list) -> Optional[str]:
            try:
                observed = [
                    r.get(cursor_field)
                    for r in rows
                    if isinstance(r, dict) and r.get(cursor_field) is not None
                ]
                return str(max(observed)) if observed else None
            except (TypeError, ValueError) as exc:
                logger.warning(
                    f"Could not compute cursor max for field={cursor_field!r}: {exc}"
                )
                return None

        cursor_end_value = cursor_override_end
        if cursor_field:
            run_cursor = _max_cursor(flattened_records)
            if run_cursor is None:
                run_cursor = _max_cursor(valid_rows)
            if run_cursor is not None:
                cursor_end_value = run_cursor

        task_run.cursor_end = cursor_end_value
        task_run.ended_at = datetime.now(timezone.utc)

        # Watermark advancement: ONLY on full SUCCESS. PARTIAL_SUCCESS leaves
        # the watermark where it was so any failed row gets re-fetched on the
        # next incremental run instead of being silently skipped forever
        # (CodeRabbit-flagged correctness bug). Backfill / replay never advance.
        if (
            cursor_end_value is not None
            and not is_backfill
            and not is_replay
            and task_run.status == TaskStatus.SUCCESS.value
        ):
            task.cursor_last_value = cursor_end_value
            db.add(task)

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
            "cursor_start": task_run.cursor_start,
            "cursor_end": task_run.cursor_end,
            "is_backfill": task_run.is_backfill,
            "is_replay": task_run.is_replay,
            "replay_of_run_id": task_run.replay_of_run_id,
        }
        
    except Exception as e:
        logger.error(f"Import failed for task {task_id}: {str(e)}")
        
        # Update TaskRun status to FAILED
        if task_run_id:
            task_run = db.get(TaskRun, task_run_id)
            if task_run:
                task_run.status = TaskStatus.FAILED.value
                task_run.ended_at = datetime.now(timezone.utc)
                task_run.error_message = str(e)
                db.commit()
                
                log_step(db, task_run_id, "ERROR", f"Fatal error: {str(e)}")
        
        raise
    
    finally:
        # Clear logging context
        clear_task_context()
        if close_destination_db and destination_db is not None:
            destination_db.close()
        if close_db:
            db.close()


def insert_batch(
    db: Session,
    table_name: str,
    rows: list[dict],
    batch_size: int = 500
) -> int:
    """
    Insert rows into the destination table in batches with transaction handling

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
    app_db: Session | None = None,
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

    if app_db is None:
        app_db = db

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
                    db=app_db,
                    task_run_id=task_run_id,
                    row_number=idx,
                    column_name="_upsert",
                    error_type="UPSERT_ERROR",
                    error_message=result.message,
                    source_value=result.record_key
                )

        except Exception as e:
            # Catch-all: log and continue to next record (NEVER stop)
            logger.error(f"Unexpected error processing row {idx}: {e}")
            results["errors"] += 1
            results["error_details"].append({
                "row_index": idx,
                "error": str(e)
            })

            if not task.continue_on_error:
                logger.warning("continue_on_error is False, stopping processing")
                raise

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


def _should_skip(task: Task, existing_record: dict) -> bool:
    """Check if record should be skipped based on skip_column/skip_value."""
    if not task.skip_column or not task.skip_value:
        return False

    current_value = existing_record.get(task.skip_column.upper())  # Oracle returns uppercase
    if current_value is None:
        current_value = existing_record.get(task.skip_column.lower())
    if current_value is None:
        current_value = existing_record.get(task.skip_column)

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
