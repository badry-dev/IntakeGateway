import re
from datetime import date, datetime
from typing import Any


class ValidationError:
    """Represents a validation error for a specific field"""

    def __init__(self, column: str, error_type: str, message: str, value: Any = None):
        self.column = column
        self.error_type = error_type
        self.message = message
        self.value = value

    def to_dict(self) -> dict:
        return {
            "column": self.column,
            "error_type": self.error_type,
            "message": self.message,
            "value": self.value,
        }


def validate_required(column: str, value: Any) -> ValidationError | None:
    """Check if required field is not None/empty"""
    if value is None or value == "":
        return ValidationError(
            column=column,
            error_type="required",
            message=f"Field {column} is required",
            value=value,
        )
    return None


def validate_type(column: str, value: Any, expected_type: str) -> ValidationError | None:
    """Validate value matches expected type"""
    if value is None:
        return None

    type_validators = {
        "int": lambda v: (
            (isinstance(v, int) and not isinstance(v, bool)) or (isinstance(v, str) and v.isdigit())
        ),
        "float": lambda v: (
            (isinstance(v, (int, float)) and not isinstance(v, bool))
            or (isinstance(v, str) and is_float(v))
        ),
        "string": lambda v: (
            isinstance(v, str) or (isinstance(v, (int, float)) and not isinstance(v, bool))
        ),  # Coerce numbers to string, reject booleans
        "bool": lambda v: (
            isinstance(v, bool)
            or (isinstance(v, str) and v.lower() in ("true", "false", "1", "0", "yes", "no"))
            or isinstance(v, int)
        ),
        "date": lambda v: is_valid_date(v),
        "datetime": lambda v: is_valid_datetime(v),
    }

    validator = type_validators.get(expected_type)
    if validator and not validator(value):
        return ValidationError(
            column=column,
            error_type="type",
            message=f"Field {column} expected type {expected_type}",
            value=value,
        )
    return None


def validate_length(column: str, value: Any, max_length: int) -> ValidationError | None:
    """Validate string length does not exceed max"""
    if value is None or not isinstance(value, str):
        return None

    if len(value) > max_length:
        return ValidationError(
            column=column,
            error_type="length",
            message=f"Field {column} exceeds max length {max_length}",
            value=value,
        )
    return None


def validate_format(column: str, value: Any, format_type: str) -> ValidationError | None:
    """Validate value matches expected format (email, phone, etc.)"""
    if value is None:
        return None

    if not isinstance(value, str):
        return ValidationError(
            column=column,
            error_type="format",
            message=f"Field {column} must be a string for format validation",
            value=value,
        )

    format_patterns = {
        "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "phone": r"^\+?[\d\s\-\(\)]{7,20}$",
        "url": r"^https?://[^\s/$.?#].[^\s]*$",
        "uuid": r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        "iso_date": r"^\d{4}-\d{2}-\d{2}$",
    }

    pattern = format_patterns.get(format_type, format_type)  # Allow custom regex
    if pattern and not re.match(pattern, value, re.IGNORECASE if format_type == "uuid" else 0):
        return ValidationError(
            column=column,
            error_type="format",
            message=f"Field {column} does not match expected format {format_type}",
            value=value,
        )
    return None


def validate_range(
    column: str, value: Any, min_val: Any = None, max_val: Any = None
) -> ValidationError | None:
    """Validate numeric value is within min/max range"""
    if value is None or not isinstance(value, (int, float)):
        return None

    if min_val is not None and value < min_val:
        return ValidationError(
            column=column,
            error_type="range",
            message=f"Field {column} value must be at least {min_val}",
            value=value,
        )

    if max_val is not None and value > max_val:
        return ValidationError(
            column=column,
            error_type="range",
            message=f"Field {column} value must be at most {max_val}",
            value=value,
        )

    return None


# Helper functions
def is_float(value: str) -> bool:
    """Check if string can be converted to float"""
    try:
        float(value)
        return True
    except (ValueError, TypeError):
        return False


def is_valid_date(value: Any) -> bool:
    """Check if value is a valid date"""
    if isinstance(value, date) and not isinstance(value, datetime):
        return True
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y"):
            try:
                datetime.strptime(value, fmt).date()
                return True
            except ValueError:
                continue
    return False


def is_valid_datetime(value: Any) -> bool:
    """Check if value is a valid datetime"""
    if isinstance(value, datetime):
        return True
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f"):
            try:
                datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
    return False


def validate_row(row: dict[str, Any], column_specs: dict[str, dict]) -> list[ValidationError]:
    """
    Validate a row against column specifications

    Args:
        row: Dictionary with column values
        column_specs: Dict mapping column names to spec dicts with keys:
            - required: whether field is required (default False)
            - type: expected data type (optional)
            - max_length: maximum string length (optional)
            - format: expected format (email, phone, etc.) (optional)
            - min: minimum numeric value (optional)
            - max: maximum numeric value (optional)

    Returns:
        List of ValidationError objects
    """
    errors: list[ValidationError] = []

    for column, col_spec in column_specs.items():
        value = row.get(column)

        # Check if required
        if col_spec.get("required", False):
            error = validate_required(column, value)
            if error:
                errors.append(error)
                continue  # Skip further validation if required check fails

        # Skip validation if value is None
        if value is None:
            continue

        # Type validation
        if "type" in col_spec:
            error = validate_type(column, value, col_spec["type"])
            if error:
                errors.append(error)

        # Length validation
        if "max_length" in col_spec:
            error = validate_length(column, value, col_spec["max_length"])
            if error:
                errors.append(error)

        # Format validation
        if "format" in col_spec:
            error = validate_format(column, value, col_spec["format"])
            if error:
                errors.append(error)

        # Range validation
        if "min" in col_spec or "max" in col_spec:
            error = validate_range(column, value, col_spec.get("min"), col_spec.get("max"))
            if error:
                errors.append(error)

    return errors


def validate_rows(
    rows: list[dict[str, Any]], column_specs: dict[str, dict]
) -> tuple[list[dict], list[dict]]:
    """
    Validate multiple rows and separate valid/invalid

    Args:
        rows: List of row dictionaries
        column_specs: Column specifications dictionary

    Returns:
        Tuple of (valid_rows, invalid_rows_with_errors)
        invalid_rows_with_errors contains dicts with 'row' and 'errors' keys
    """
    valid_rows = []
    invalid_rows = []

    for row in rows:
        errors = validate_row(row, column_specs)
        if errors:
            invalid_rows.append({"row": row, "errors": errors})
        else:
            valid_rows.append(row)

    return valid_rows, invalid_rows
