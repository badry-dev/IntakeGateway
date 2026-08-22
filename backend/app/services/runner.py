import hashlib
import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError, IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import clear_task_context, set_task_context
from app.db.models.task import Task
from app.db.models.task_log import TaskLog
from app.db.models.task_run import TaskRun, TaskStatus
from app.db.models.task_run_log import TaskRunLog
from app.db.session import SessionLocal
from app.services import api_connector, mapper, normalizer, validator
from app.services.connection_pool import get_session as get_destination_session

# Cursor identifiers go directly into URL query params; whitelist them strictly.
_SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,99}$")
_SAFE_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_$#]{0,127}$")


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


class RowStatus(StrEnum):
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
    cursor_override_start: str | None = None,
    cursor_override_end: str | None = None,
    is_backfill: bool = False,
    replay_of_run_id: int | None = None,
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
            started_at=datetime.now(UTC),
            cursor_start=cursor_start_value,
            is_backfill=is_backfill,
            is_replay=is_replay,
            replay_of_run_id=replay_of_run_id,
            rows_fetched=0,
            rows_inserted=0,
            rows_updated=0,
            rows_skipped=0,
            error_count=0,
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
                    raise ValueError(f"Derived cursor end param name {end_param!r} is invalid")
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
        log_step(
            db, task_run_id, "EXTRACT_RECORDS", f"Extracting records with path: {task.record_path}"
        )

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
            task_run.ended_at = datetime.now(UTC)
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

        if not column_mappings:
            raise ValueError(
                f"No active column mappings configured for task {task_id}. "
                "Configure mappings before running the task; direct API-field inserts are disabled."
            )

        # Debug: Log source field names and sample values
        if flattened_records:
            sample_record = flattened_records[0]
            logger.debug(f"Sample flattened record keys: {list(sample_record.keys())}")
            logger.debug(f"Sample flattened record: {sample_record}")
            for mapping in column_mappings:
                source_val = sample_record.get(mapping.source_field)
                logger.debug(
                    f"Mapping: {mapping.source_field} -> {mapping.dest_column} "
                    f"| transforms={mapping.transform_rules} | source_value={repr(source_val)}"
                )

        mapped_records = mapper.map_rows(flattened_records, column_mappings)

        # Debug: Log mapped results
        if mapped_records:
            sample_mapped = mapped_records[0]
            logger.debug(f"Sample mapped record: {sample_mapped}")

        # Step 7: Validate rows
        log_step(db, task_run_id, "VALIDATE", f"Validating {len(mapped_records)} records")

        # Build column specs from task configuration (simplified - could be enhanced)
        column_specs = {}  # Empty dict = no validation rules (accept all data as-is)

        valid_rows, invalid_rows = validator.validate_rows(mapped_records, column_specs)

        logger.info(f"Validation complete: {len(valid_rows)} valid, {len(invalid_rows)} invalid")

        # Step 8: Log validation errors
        for idx, invalid_item in enumerate(invalid_rows):
            errors = invalid_item["errors"]
            for error in errors:
                log_row_error(
                    db=db,
                    task_run_id=task_run_id,
                    row_number=idx,
                    column_name=error.column,
                    error_type=error.error_type,
                    error_message=error.message,
                    source_value=str(error.value) if error.value is not None else None,
                )

        task_run.error_count = len(invalid_rows)
        db.commit()

        # Step 9: Insert/Upsert valid rows to the configured destination database
        if valid_rows:
            log_step(
                db,
                task_run_id,
                "CONNECT_DESTINATION",
                "Opening destination database session",
            )

            if destination_db is None:
                destination_db = get_destination_session(task.connection_id)
                close_destination_db = True

            if task.upsert_enabled:
                # Use upsert logic with skip conditions
                log_step(
                    db,
                    task_run_id,
                    "UPSERT_DB",
                    f"Upserting {len(valid_rows)} rows to {task.dest_table}",
                )

                upsert_results = process_rows_with_upsert(
                    db=destination_db,
                    task=task,
                    task_run_id=task_run_id,
                    app_db=db,
                    rows=valid_rows,
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
                log_step(
                    db,
                    task_run_id,
                    "INSERT_DB",
                    f"Inserting {len(valid_rows)} rows to {task.dest_table}",
                )

                rows_inserted = insert_batch(
                    db=destination_db,
                    table_name=task.dest_table,
                    rows=valid_rows,
                    batch_size=task.batch_size,
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

        def _max_cursor(rows: list) -> str | None:
            try:
                observed = [
                    r.get(cursor_field)
                    for r in rows
                    if isinstance(r, dict) and r.get(cursor_field) is not None
                ]
                return str(max(observed)) if observed else None
            except (TypeError, ValueError) as exc:
                logger.warning(f"Could not compute cursor max for field={cursor_field!r}: {exc}")
                return None

        cursor_end_value = cursor_override_end
        if cursor_field:
            run_cursor = _max_cursor(flattened_records)
            if run_cursor is None:
                run_cursor = _max_cursor(valid_rows)
            if run_cursor is not None:
                cursor_end_value = run_cursor

        task_run.cursor_end = cursor_end_value
        task_run.ended_at = datetime.now(UTC)

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
                task_run.ended_at = datetime.now(UTC)
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


def _clean_identifier(identifier: str) -> str:
    """Normalize a user/API-provided identifier before validating it."""
    cleaned = str(identifier).strip()
    if len(cleaned) >= 2 and cleaned[0] == '"' and cleaned[-1] == '"':
        cleaned = cleaned[1:-1].replace('""', '"')
    if not _SAFE_SQL_IDENTIFIER_RE.match(cleaned):
        raise ValueError(f"Invalid SQL identifier: {identifier!r}")
    return cleaned


def _format_table_name(table_name: str) -> str:
    """Validate schema-qualified table names while preserving unquoted Oracle semantics."""
    parts = str(table_name).split(".")
    return ".".join(_clean_identifier(part) for part in parts)


def _quote_column_name(column_name: str) -> str:
    """Quote column identifiers so reserved words like CHECK/MODE are valid columns."""
    cleaned = _clean_identifier(column_name)
    return f'"{cleaned.replace(chr(34), chr(34) * 2)}"'


def _build_insert_statement(
    table_name: str, columns: list[str], sample_row: dict | None = None
) -> tuple[str, list[str], dict[str, str]]:
    """
    Build INSERT statement with TO_DATE() wrapping for date-formatted strings.

    Args:
        table_name: Target table name
        columns: List of column names
        sample_row: Optional sample row to detect date columns

    Returns:
        Tuple of (SQL string, columns list, bind_map dict)
    """
    import re

    bind_names = [f"p{idx}" for idx in range(len(columns))]
    column_str = ", ".join(_quote_column_name(column) for column in columns)

    # Debug: Log sample row
    if sample_row:
        logger.debug(f"Sample row for date detection: {sample_row}")

    # Build placeholders, wrapping date strings with TO_DATE()
    placeholders = []
    for idx, column in enumerate(columns):
        bind_name = bind_names[idx]

        # Check if this column's value looks like a date string (YYYY-MM-DD)
        is_date_string = False
        if sample_row and column in sample_row:
            value = sample_row[column]
            if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                is_date_string = True
                logger.debug(f"Detected date column: {column} = {value}")

        if is_date_string:
            # Wrap with TO_DATE() for Oracle DATE columns
            placeholders.append(f"TO_DATE(:{bind_name}, 'YYYY-MM-DD')")
        else:
            placeholders.append(f":{bind_name}")

    insert_sql = f"INSERT INTO {_format_table_name(table_name)} ({column_str}) VALUES ({', '.join(placeholders)})"

    # Debug: Log generated SQL
    logger.debug(f"Generated INSERT SQL: {insert_sql}")

    return insert_sql, columns, dict(zip(columns, bind_names, strict=True))


def _rows_for_bind_aliases(
    rows: list[dict], columns: list[str], bind_map: dict[str, str]
) -> list[dict]:
    return [{bind_map[column]: row.get(column) for column in columns} for row in rows]


def insert_batch(db: Session, table_name: str, rows: list[dict], batch_size: int = 500) -> int:
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
        batch = rows[i : i + batch_size]

        try:
            # Build dynamic INSERT statement
            if batch:
                columns = list(batch[0].keys())
                insert_sql, columns, bind_map = _build_insert_statement(
                    table_name, columns, batch[0]
                )
                bind_rows = _rows_for_bind_aliases(batch, columns, bind_map)

                # Execute batch insert
                db.execute(text(insert_sql), bind_rows)
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
    Process rows with BATCHED upsert logic and skip conditions.
    Uses bulk SELECT + bulk INSERT/UPDATE for performance.

    Args:
        db: SQLAlchemy session
        task: Task configuration with upsert settings
        task_run_id: ID of current run for logging
        rows: List of row dictionaries to process

    Returns:
        Dictionary with processing statistics
    """
    results = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0, "error_details": []}

    if not rows:
        return results

    if app_db is None:
        app_db = db

    # Parse upsert_keys - handle both string (JSON) and list formats
    if not task.upsert_keys:
        upsert_keys = []
    elif isinstance(task.upsert_keys, list):
        upsert_keys = task.upsert_keys
    elif isinstance(task.upsert_keys, str):
        upsert_keys = json.loads(task.upsert_keys)
    else:
        upsert_keys = []

    if not upsert_keys:
        # No upsert keys - just bulk insert
        logger.warning("No upsert keys configured, falling back to bulk insert")
        try:
            total = insert_batch(db, task.dest_table, rows)
            results["inserted"] = total
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Bulk insert failed: {e}")
            results["errors"] = len(rows)
        return results

    # Process in batches for better performance and memory management
    BATCH_SIZE = 500

    for batch_start in range(0, len(rows), BATCH_SIZE):
        batch = rows[batch_start : batch_start + BATCH_SIZE]
        batch_results = _process_upsert_batch(
            db=db,
            task=task,
            task_run_id=task_run_id,
            batch=batch,
            batch_offset=batch_start,
            upsert_keys=upsert_keys,
            app_db=app_db,
        )

        # Aggregate results
        results["inserted"] += batch_results["inserted"]
        results["updated"] += batch_results["updated"]
        results["skipped"] += batch_results["skipped"]
        results["errors"] += batch_results["errors"]
        results["error_details"].extend(batch_results["error_details"])

        logger.info(
            f"Batch {batch_start}-{batch_start + len(batch)}: "
            f"inserted={batch_results['inserted']}, "
            f"updated={batch_results['updated']}, "
            f"skipped={batch_results['skipped']}, "
            f"errors={batch_results['errors']}"
        )

    return results


def _process_upsert_batch(
    db: Session,
    task: Task,
    task_run_id: int,
    batch: list[dict],
    batch_offset: int,
    upsert_keys: list[str],
    app_db: Session,
) -> dict:
    """
    Process a single batch of rows with bulk operations.

    Strategy:
    1. SELECT all existing records in one query (by upsert keys)
    2. Split batch into: to_insert, to_update, to_skip
    3. Bulk UPDATE existing records (one query)
    4. Bulk INSERT new records (one query)
    """

    results = {"inserted": 0, "updated": 0, "skipped": 0, "errors": 0, "error_details": []}

    if not batch:
        return results

    # Deduplicate rows sharing the same upsert-key tuple WITHIN this batch.
    # Two rows with identical keys would both enter to_update (later WHEN
    # clauses silently dropped by SQL) or both to_insert (constraint failure
    # or duplicate rows). First occurrence wins; duplicates are counted as
    # skipped with an attribution entry.
    seen_keys = set()
    deduped_batch = []
    for idx, row in enumerate(batch):
        key_tuple = tuple(row.get(key) for key in upsert_keys)
        if key_tuple in seen_keys:
            results["skipped"] += 1
            results["error_details"].append(
                {
                    "row_index": batch_offset + idx,
                    "record_key": _get_record_key(row, upsert_keys),
                    "error": "duplicate upsert key within batch; first occurrence wins",
                }
            )
            continue
        seen_keys.add(key_tuple)
        deduped_batch.append(row)
    batch = deduped_batch

    if not batch:
        return results

    try:
        # Step 1: Fetch ALL existing records in one SELECT query
        table_name = task.dest_table

        # Build WHERE clause: (key1=val1 AND key2=val2) OR (key1=val3 AND key2=val4) ...
        # This fetches all matching records in a single query

        # Create a table reference for raw SQL
        where_clauses = []
        for row in batch:
            key_conditions = []
            for key in upsert_keys:
                key_conditions.append(f"{_quote_column_name(key)} = :{key}_{id(row)}")
            where_clauses.append(f"({' AND '.join(key_conditions)})")

        where_sql = " OR ".join(where_clauses)

        # Build params dict
        params = {}
        for row in batch:
            for key in upsert_keys:
                params[f"{key}_{id(row)}"] = row.get(key)

        # Include the skip column in the projection when a skip condition is
        # configured so matching rows can be routed to `to_skip` without a
        # second per-row query.
        select_columns = list(upsert_keys)
        if task.skip_column and task.skip_value is not None:
            skip_col = _clean_identifier(task.skip_column)
            if skip_col not in select_columns:
                select_columns.append(skip_col)

        select_sql = f"SELECT {', '.join(_quote_column_name(k) for k in select_columns)} FROM {_format_table_name(table_name)} WHERE {where_sql}"

        existing_result = db.execute(text(select_sql), params).fetchall()

        # Build map of existing record keys -> fetched column values for fast lookup
        existing_rows = {}
        for row in existing_result:
            mapping = dict(row._mapping)
            key_tuple = tuple(
                mapping.get(key, mapping.get(key.upper(), mapping.get(key.lower())))
                for key in upsert_keys
            )
            existing_rows[key_tuple] = mapping

        logger.debug(f"Found {len(existing_rows)} existing records out of {len(batch)}")

        # Step 2: Split batch into insert/update/skip lists
        to_insert = []
        to_update = []
        to_skip = []

        for idx, row in enumerate(batch):
            row_key_tuple = tuple(row.get(key) for key in upsert_keys)
            existing = existing_rows.get(row_key_tuple)

            if existing is None:
                # New record
                to_insert.append((batch_offset + idx, row))
            elif task.skip_column and task.skip_value is not None and _should_skip(task, existing):
                # Record exists and matches the configured skip condition —
                # third parties may have marked this row processed; never
                # overwrite it.
                to_skip.append((batch_offset + idx, row))
            else:
                to_update.append((batch_offset + idx, row))

        # Steps 3+4: Bulk UPDATE + INSERT inside a savepoint, so a partially
        # applied bulk statement is rolled back completely before falling back
        # to per-row processing (a replayed half-applied batch would corrupt
        # data). The batch commits exactly once.
        if to_update or to_insert:
            try:
                with db.begin_nested():
                    if to_update:
                        results["updated"] = _bulk_update_rows(db, task, to_update, upsert_keys)
                        logger.debug(f"Bulk updated {results['updated']} rows")
                    if to_insert:
                        insert_rows = [row for _, row in to_insert]
                        results["inserted"] = insert_batch(db, task.dest_table, insert_rows)
                        logger.debug(f"Bulk inserted {results['inserted']} rows")
                db.commit()
            except Exception as bulk_exc:
                db.rollback()
                logger.warning(
                    f"Bulk upsert failed ({bulk_exc}); falling back to row-by-row "
                    f"for this batch of {len(batch)} rows"
                )
                # Per-row fallback preserves error attribution and the
                # "never stop on row errors" contract; _process_single_row
                # includes the fixed skip-condition logic.
                for idx, row in to_update + to_insert:
                    row_result = _process_single_row(db, task, row, idx)
                    if row_result.status == RowStatus.UPDATED:
                        results["updated"] += 1
                    elif row_result.status == RowStatus.INSERTED:
                        results["inserted"] += 1
                    elif row_result.status == RowStatus.SKIPPED:
                        results["skipped"] += 1
                    else:
                        results["errors"] += 1
                        results["error_details"].append(
                            {
                                "row_index": idx,
                                "record_key": row_result.record_key,
                                "error": str(row_result.message)[:500],
                            }
                        )

        results["skipped"] += len(to_skip)

    except Exception as e:
        db.rollback()
        logger.error(f"Batch upsert failed: {e}")
        results["errors"] = len(batch)
        results["error_details"].append(
            {"batch_start": batch_offset, "batch_size": len(batch), "error": str(e)[:500]}
        )

    return results


def _bulk_update_rows(
    db: Session,
    task: Task,
    rows_with_idx: list[tuple[int, dict]],
    upsert_keys: list[str],
) -> int:
    """
    Bulk update multiple rows using CASE statements.

    Generates SQL like:
    UPDATE table SET
      col1 = CASE
        WHEN key1=val1 THEN newval1
        WHEN key1=val2 THEN newval2
        ...
        ELSE col1
      END,
      col2 = CASE ... ELSE col2 END
    WHERE (key1=val1) OR (key1=val2) OR ...

    The `ELSE <col>` branch preserves the existing value for rows whose
    incoming value is None — without it the CASE evaluates to NULL and would
    overwrite NOT NULL columns, reintroducing ORA-01407.
    """
    import re

    if not rows_with_idx:
        return 0

    table_name = task.dest_table

    # Columns to update: deterministic first-seen union of non-key columns
    # across ALL rows. Deriving them from the first row only would silently
    # drop columns that happen to be absent/None in row 1 but present in later
    # rows.
    update_cols = []
    seen_cols = set()
    for _, row in rows_with_idx:
        for col in row.keys():
            if col not in upsert_keys and col not in seen_cols:
                seen_cols.add(col)
                update_cols.append(col)

    if not update_cols:
        return 0  # Nothing to update

    # Build CASE statements for each column
    set_clauses = []
    params = {}
    param_counter = 0

    for col in update_cols:
        case_whens = []
        for idx, row in rows_with_idx:
            # Get the value for this column
            value = row.get(col)

            # Rows with a None value get no WHEN clause; the CASE's ELSE
            # branch below preserves the stored value instead of writing NULL.
            if value is None:
                continue

            # Build condition: key1=val1 AND key2=val2
            conditions = []
            for key in upsert_keys:
                param_name = f"k{param_counter}"
                param_counter += 1
                conditions.append(f"{_quote_column_name(key)} = :{param_name}")
                params[param_name] = row.get(key)

            condition_sql = " AND ".join(conditions)

            param_name = f"v{param_counter}"
            param_counter += 1

            # Check if this is a date string that needs TO_DATE()
            if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                case_whens.append(f"WHEN {condition_sql} THEN TO_DATE(:{param_name}, 'YYYY-MM-DD')")
            else:
                case_whens.append(f"WHEN {condition_sql} THEN :{param_name}")

            params[param_name] = value

        # Only add this column to SET clause if at least one row has a non-None value
        if case_whens:
            # ELSE keeps the existing column value for any row in the WHERE
            # scope whose incoming value for this column is None.
            case_sql = (
                f"{_quote_column_name(col)} = CASE {' '.join(case_whens)} "
                f"ELSE {_quote_column_name(col)} END"
            )
            set_clauses.append(case_sql)

    # If no columns to update (all rows had None values for all columns), skip UPDATE
    if not set_clauses:
        logger.info(f"Skipping UPDATE for {len(rows_with_idx)} rows: all values are None")
        return 0

    # Build WHERE clause: (key1=val1 AND key2=val2) OR (key1=val3 AND key2=val4) ...
    where_conditions = []
    for idx, row in rows_with_idx:
        key_conditions = []
        for key in upsert_keys:
            param_name = f"w{param_counter}"
            param_counter += 1
            key_conditions.append(f"{_quote_column_name(key)} = :{param_name}")
            params[param_name] = row.get(key)
        where_conditions.append(f"({' AND '.join(key_conditions)})")

    where_sql = " OR ".join(where_conditions)

    update_sql = (
        f"UPDATE {_format_table_name(table_name)} SET {', '.join(set_clauses)} WHERE {where_sql}"
    )

    result = db.execute(text(update_sql), params)
    return result.rowcount


def _process_single_row(db: Session, task: Task, row: dict, row_index: int) -> RowResult:
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
                    message=f"Skip condition met: {task.skip_column}={task.skip_value}",
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
        return RowResult(status=RowStatus.ERROR, record_key=record_key, message=error_msg)

    except DatabaseError as e:
        # Other database errors
        db.rollback()
        error_msg = f"Database error: {str(e)[:200]}"
        logger.error(f"Row {row_index} ({record_key}): {error_msg}")
        return RowResult(status=RowStatus.ERROR, record_key=record_key, message=error_msg)


def _get_record_key(row: dict, upsert_keys: list) -> str:
    """Generate a readable key for logging."""
    if upsert_keys:
        return ", ".join(f"{k}={row.get(k)}" for k in upsert_keys)
    return f"row_{id(row)}"


def _find_existing_record(
    db: Session, table_name: str, row: dict, upsert_keys: list
) -> dict | None:
    """Check if a record exists in the database based on upsert keys."""
    if not upsert_keys:
        return None

    bind_map = {key: f"k{idx}" for idx, key in enumerate(upsert_keys)}
    where_clauses = " AND ".join(
        f"{_quote_column_name(key)} = :{bind_map[key]}" for key in upsert_keys
    )
    params = {bind_map[key]: row.get(key) for key in upsert_keys}

    query = f"SELECT * FROM {_format_table_name(table_name)} WHERE {where_clauses}"
    result = db.execute(text(query), params).fetchone()

    if result:
        # Convert to dictionary
        return dict(result._mapping)
    return None


def _should_skip(task: Task, existing_record: dict) -> bool:
    """Check if record should be skipped based on skip_column/skip_value."""
    if not task.skip_column or task.skip_value is None:
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
    insert_sql, columns, bind_map = _build_insert_statement(table_name, columns, row)
    bind_row = _rows_for_bind_aliases([row], columns, bind_map)[0]
    db.execute(text(insert_sql), bind_row)


def _update_existing_row(db: Session, table_name: str, row: dict, upsert_keys: list):
    """Update an existing row in the table."""
    import re

    # Only update columns with non-None values (skip NULL to avoid NOT NULL constraint violations)
    update_cols = [col for col in row.keys() if col not in upsert_keys and row.get(col) is not None]

    if not update_cols:
        return  # Nothing to update

    update_bind_map = {col: f"u{idx}" for idx, col in enumerate(update_cols)}
    key_bind_map = {key: f"k{idx}" for idx, key in enumerate(upsert_keys)}

    # Build SET clause with TO_DATE() for date-formatted strings
    set_clauses = []
    for col in update_cols:
        bind_name = update_bind_map[col]
        value = row.get(col)

        # Check if value is a date string (YYYY-MM-DD)
        if isinstance(value, str) and re.match(r"^\d{4}-\d{2}-\d{2}$", value):
            set_clauses.append(f"{_quote_column_name(col)} = TO_DATE(:{bind_name}, 'YYYY-MM-DD')")
        else:
            set_clauses.append(f"{_quote_column_name(col)} = :{bind_name}")

    set_clause = ", ".join(set_clauses)

    where_clause = " AND ".join(
        f"{_quote_column_name(key)} = :{key_bind_map[key]}" for key in upsert_keys
    )
    params = {
        **{update_bind_map[col]: row.get(col) for col in update_cols},
        **{key_bind_map[key]: row.get(key) for key in upsert_keys},
    }

    update_sql = f"UPDATE {_format_table_name(table_name)} SET {set_clause} WHERE {where_clause}"
    db.execute(text(update_sql), params)


def log_step(db: Session, task_run_id: int, step_name: str, message: str, details: dict = None):
    """Log execution step to TaskLog table"""
    log_entry = TaskLog(
        task_run_id=task_run_id,
        step_name=step_name,
        message=message,
        details=details,  # Store as JSON dict
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
    source_value: str = None,
):
    """Log row-level validation error to TaskRunLog table.

    Stages the insert WITHOUT committing — a failing run can produce thousands
    of row errors and one commit per error previously stalled the pipeline.
    The caller commits at the pipeline-stage boundary (run_import does after
    the validation stage).
    """
    error_log = TaskRunLog(
        task_run_id=task_run_id,
        row_number=row_number,
        column_name=column_name,
        error_type=error_type,
        error_message=error_message,
        source_value=source_value,
    )
    db.add(error_log)
    return error_log
