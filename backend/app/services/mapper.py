import json
from collections.abc import Callable
from datetime import datetime
from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.db.models.column_mapping import ColumnMapping


# Transform registry for field transformations
def trim(x):
    return x.strip() if isinstance(x, str) else x


def upper(x):
    return x.upper() if isinstance(x, str) else x


def lower(x):
    return x.lower() if isinstance(x, str) else x


def to_int(x):
    if x is None or x == "":
        return None
    try:
        return int(x)
    except (ValueError, TypeError):
        return None


def to_float(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def to_bool(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        lower = x.lower()
        if lower in ("true", "1", "yes", "y"):
            return True
        if lower in ("false", "0", "no", "n"):
            return False
        return None
    return bool(x)


def to_timestamp(x):
    """Convert ISO 8601 string to Oracle TIMESTAMP format"""
    if x is None or x == "":
        return None

    try:
        if isinstance(x, str):
            # Try to parse ISO 8601 format
            # Handles: 2024-01-15T10:30:45Z, 2024-01-15T10:30:45.123Z, 2024-01-15 10:30:45
            # Remove 'Z' if present and parse
            x_clean = x.replace("Z", "+00:00") if x.endswith("Z") else x
            dt = datetime.fromisoformat(x_clean)
            # Return Oracle TIMESTAMP format: YYYY-MM-DD HH:MM:SS.ffffff
            return dt.strftime("%Y-%m-%d %H:%M:%S.%f")
        elif isinstance(x, datetime):
            return x.strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            raise ValueError(f"Cannot convert {type(x).__name__} to timestamp")
    except Exception as e:
        logger.error(f"Error converting to timestamp: {str(e)}")
        return None


def to_date(x):
    """Convert string to Oracle DATE format (YYYY-MM-DD)"""
    if x is None or x == "":
        return None

    try:
        if isinstance(x, str):
            # Try common date formats: YYYY-MM-DD, MM/DD/YYYY, DD-MM-YYYY
            date_formats = [
                "%Y-%m-%d",  # 2024-01-15
                "%m/%d/%Y",  # 01/15/2024
                "%d-%m-%Y",  # 15-01-2024
                "%Y/%m/%d",  # 2024/01/15
                "%d/%m/%Y",  # 15/01/2024
                "%Y%m%d",  # 20240115
            ]

            dt = None
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(x, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                # Try ISO format parsing as last resort
                dt = datetime.fromisoformat(x.replace("Z", "+00:00"))

            return dt.strftime("%Y-%m-%d")
        elif isinstance(x, datetime):
            return x.strftime("%Y-%m-%d")
        else:
            raise ValueError(f"Cannot convert {type(x).__name__} to date")
    except Exception as e:
        logger.error(f"Error converting to date: {str(e)}")
        return None


def format_date(x):
    """Format date/datetime with custom pattern (default ISO format)"""
    if x is None or x == "":
        return None

    try:
        if isinstance(x, str):
            # Try to parse the string first
            date_formats = [
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d-%m-%Y",
                "%Y/%m/%d",
                "%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%d %H:%M:%S",
            ]

            dt = None
            for fmt in date_formats:
                try:
                    dt = datetime.strptime(x, fmt)
                    break
                except ValueError:
                    continue

            if dt is None:
                dt = datetime.fromisoformat(x.replace("Z", "+00:00"))

            # Return ISO format
            return dt.isoformat()
        elif isinstance(x, datetime):
            return x.isoformat()
        else:
            raise ValueError(f"Cannot format {type(x).__name__}")
    except Exception as e:
        logger.error(f"Error formatting date: {str(e)}")
        return None


TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "trim": trim,
    "upper": upper,
    "lower": lower,
    "to_int": to_int,
    "to_float": to_float,
    "to_bool": to_bool,
    "to_timestamp": to_timestamp,
    "to_date": to_date,
    "format_date": format_date,
}


def apply_transform(value: Any, transform: str | None):
    """Apply a single transform to a value"""
    if not transform:
        return value
    fn = TRANSFORMS.get(transform)
    if not fn:
        raise ValueError(f"Unknown transform: {transform}")
    return fn(value)


def apply_transforms(value: Any, transform_rules: str | None) -> Any:
    """Apply multiple transforms from JSON rules to a value"""
    if not transform_rules:
        return value

    try:
        rules = json.loads(transform_rules) if isinstance(transform_rules, str) else transform_rules
    except json.JSONDecodeError:
        return value

    # Handle both dict format and list format
    if isinstance(rules, dict):
        # Format: {"transform": "upper", "trim": true}
        for transform_name, enabled in rules.items():
            if enabled and transform_name in TRANSFORMS:
                value = TRANSFORMS[transform_name](value)
    elif isinstance(rules, list):
        # Format: ["trim", "upper"]
        for transform_name in rules:
            if transform_name in TRANSFORMS:
                value = TRANSFORMS[transform_name](value)

    return value


def map_row_with_column_mappings(
    source_row: dict[str, Any], column_mappings: list[ColumnMapping]
) -> dict[str, Any]:
    """Map source fields to destination columns using ColumnMapping definitions"""
    dest_row = {}

    for mapping in column_mappings:
        if not mapping.is_active:
            continue

        source_value = source_row.get(mapping.source_field)

        # Apply transforms if defined
        if mapping.transform_rules:
            transformed_value = apply_transforms(source_value, mapping.transform_rules)
        else:
            transformed_value = source_value

        dest_row[mapping.dest_column] = transformed_value

    return dest_row


def get_column_mappings(db: Session, task_id: int) -> list[ColumnMapping]:
    """Fetch active column mappings for a task"""
    return (
        db.query(ColumnMapping)
        .filter(ColumnMapping.task_id == task_id, ColumnMapping.is_active)
        .all()
    )


def map_rows(
    source_rows: list[dict[str, Any]], column_mappings: list[ColumnMapping]
) -> list[dict[str, Any]]:
    """Map multiple rows from source to destination format"""
    return [map_row_with_column_mappings(row, column_mappings) for row in source_rows]
