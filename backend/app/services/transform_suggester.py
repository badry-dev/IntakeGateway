"""Transform suggester service for recommending transforms based on type mismatches.

Analyzes source field types (from API response) and destination column types (from Oracle)
to recommend appropriate transforms for data type compatibility.
"""

from app.db.schemas.column_mapping import (
    TransformSuggestion,
    TransformSuggestionsResponse,
)
from app.services.oracle_metadata import get_oracle_type_category
import logging

logger = logging.getLogger(__name__)


# Mapping of API field types
API_TYPES = {
    "string": "string",
    "number": "number",
    "boolean": "boolean",
    "date": "date",
    "timestamp": "timestamp",
    "array": "array",
    "object": "object",
    "null": "null",
}


def suggest_transforms(
    source_type: str, dest_type: str
) -> TransformSuggestionsResponse:
    """
    Generate transform suggestions for a source-destination type pair.

    Args:
        source_type: Type of the API response field (string, number, boolean, array, object, null)
        dest_type: Type of the Oracle column (VARCHAR2, NUMBER, DATE, TIMESTAMP, etc.)

    Returns:
        TransformSuggestionsResponse with recommended transforms

    Raises:
        ValueError: If invalid type pair
    """
    source_type_lower = source_type.lower().strip()
    dest_type_upper = dest_type.upper().strip()

    # Validate source type
    if source_type_lower not in API_TYPES:
        raise ValueError(
            f"Invalid source type '{source_type}'. "
            f"Valid types: {', '.join(API_TYPES.keys())}"
        )

    # Get destination type category
    dest_category = get_oracle_type_category(dest_type_upper)

    if dest_category == "unknown":
        logger.warning(f"Unknown destination type: {dest_type_upper}")

    # Generate suggestions based on source → destination mapping
    suggestions = []
    requires_transform = False
    warning_message = None

    # ===================================================================
    # STRING → * mappings
    # ===================================================================
    if source_type_lower == "string":
        if dest_category == "string":
            suggestions.append(
                TransformSuggestion(
                    transform_name="trim",
                    reason="Remove leading/trailing whitespace from API string",
                    priority="low",
                )
            )
        elif dest_category == "number":
            suggestions.append(
                TransformSuggestion(
                    transform_name="to_int",
                    reason="Parse string to integer for numeric column",
                    priority="high",
                )
            )
            suggestions.append(
                TransformSuggestion(
                    transform_name="to_float",
                    reason="Parse string to float for numeric column",
                    priority="high",
                )
            )
            requires_transform = True
        elif dest_category == "date":
            suggestions.append(
                TransformSuggestion(
                    transform_name="to_date",
                    reason="Convert ISO date string (YYYY-MM-DD) to Oracle DATE",
                    priority="high",
                )
            )
            requires_transform = True
        elif dest_category == "timestamp":
            suggestions.append(
                TransformSuggestion(
                    transform_name="to_timestamp",
                    reason="Convert ISO 8601 datetime string to Oracle TIMESTAMP",
                    priority="high",
                )
            )
            requires_transform = True
        elif dest_category == "binary":
            warning_message = (
                f"String to {dest_type_upper} conversion requires manual implementation"
            )

    # ===================================================================
    # NUMBER → * mappings
    # ===================================================================
    elif source_type_lower == "number":
        if dest_category == "string":
            # No transform needed, Oracle implicit conversion
            suggestions.append(
                TransformSuggestion(
                    transform_name="trim",
                    reason="Optional: clean up any formatting (though number→string is implicit)",
                    priority="low",
                )
            )
        elif dest_category == "number":
            # Same type, no transformation needed
            pass
        elif dest_category == "date" or dest_category == "timestamp":
            warning_message = f"Number to {dest_type_upper} requires domain knowledge (epoch vs milliseconds vs days)"

    # ===================================================================
    # BOOLEAN → * mappings
    # ===================================================================
    elif source_type_lower == "boolean":
        if dest_category == "string":
            # Boolean can be stored as string 'true'/'false'
            suggestions.append(
                TransformSuggestion(
                    transform_name="trim",
                    reason="Convert boolean to string representation",
                    priority="medium",
                )
            )
        elif dest_category == "number":
            suggestions.append(
                TransformSuggestion(
                    transform_name="to_int",
                    reason="Convert boolean to 1/0 for numeric column",
                    priority="high",
                )
            )
            requires_transform = True
        else:
            warning_message = (
                f"Boolean to {dest_type_upper} conversion is not straightforward"
            )

    # ===================================================================
    # DATE → * mappings
    # ===================================================================
    elif source_type_lower == "date":
        if dest_category == "string":
            suggestions.append(
                TransformSuggestion(
                    transform_name="format_date",
                    reason="Format date to string representation",
                    priority="low",
                )
            )
        elif dest_category == "date" or dest_category == "timestamp":
            # Date to DATE/TIMESTAMP is straightforward
            pass
        else:
            warning_message = (
                f"Date to {dest_type_upper} conversion requires custom logic"
            )

    # ===================================================================
    # TIMESTAMP → * mappings
    # ===================================================================
    elif source_type_lower == "timestamp":
        if dest_category == "string":
            suggestions.append(
                TransformSuggestion(
                    transform_name="format_date",
                    reason="Format timestamp to string representation",
                    priority="low",
                )
            )
        elif dest_category == "timestamp" or dest_category == "date":
            # Timestamp to TIMESTAMP is straightforward
            pass
        else:
            warning_message = (
                f"Timestamp to {dest_type_upper} conversion requires custom logic"
            )

    # ===================================================================
    # ARRAY / OBJECT → * mappings
    # ===================================================================
    elif source_type_lower in ("array", "object"):
        warning_message = (
            f"Cannot map {source_type_lower} directly to {dest_type_upper}. "
            f"Consider extracting a specific field from the {source_type_lower}."
        )
        requires_transform = True

    # ===================================================================
    # NULL → * mappings
    # ===================================================================
    elif source_type_lower == "null":
        warning_message = (
            "Source field contains only null values. No transformation possible."
        )
        requires_transform = True

    logger.info(
        f"Generated {len(suggestions)} suggestions for {source_type_lower} → {dest_type_upper} "
        f"(requires_transform={requires_transform})"
    )

    return TransformSuggestionsResponse(
        source_type=source_type_lower,
        dest_type=dest_type_upper,
        suggestions=suggestions,
        requires_transform=requires_transform,
        warning_message=warning_message,
    )


def validate_transforms(transforms: list[str]) -> tuple[bool, list[str]]:
    """
    Validate that all transforms in a list are recognized.

    Args:
        transforms: List of transform names

    Returns:
        Tuple of (is_valid, invalid_transforms)
    """
    valid_transforms = {
        "trim",
        "upper",
        "lower",
        "to_int",
        "to_float",
        "to_bool",
        "to_timestamp",
        "to_date",
        "format_date",
    }

    invalid_transforms = [t for t in transforms if t not in valid_transforms]

    return len(invalid_transforms) == 0, invalid_transforms


def get_available_transforms() -> list[str]:
    """
    Get list of all available transforms.

    Returns:
        List of transform names
    """
    return [
        "trim",
        "upper",
        "lower",
        "to_int",
        "to_float",
        "to_bool",
        "to_timestamp",
        "to_date",
        "format_date",
    ]


def get_transform_description(transform_name: str) -> str:
    """
    Get human-readable description of a transform.

    Args:
        transform_name: Name of the transform

    Returns:
        Description string
    """
    descriptions = {
        "trim": "Remove leading and trailing whitespace",
        "upper": "Convert to uppercase",
        "lower": "Convert to lowercase",
        "to_int": "Parse as integer (rounded down)",
        "to_float": "Parse as floating point number",
        "to_bool": "Parse as boolean (true/1/yes/y → True)",
        "to_timestamp": "Parse ISO 8601 string to Oracle TIMESTAMP",
        "to_date": "Parse YYYY-MM-DD string to Oracle DATE",
        "format_date": "Format date/timestamp to custom string format",
    }
    return descriptions.get(transform_name, f"Transform '{transform_name}'")
