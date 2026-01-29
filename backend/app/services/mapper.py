
from typing import Any, Callable
from sqlalchemy.orm import Session
from app.db.models.column_mapping import ColumnMapping
import json

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
    return int(x)

def to_float(x):
    if x is None or x == "":
        return None
    return float(x)

def to_bool(x):
    if isinstance(x, bool):
        return x
    if isinstance(x, str):
        return x.lower() in ("true", "1", "yes", "y")
    return bool(x)

TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "trim": trim,
    "upper": upper,
    "lower": lower,
    "to_int": to_int,
    "to_float": to_float,
    "to_bool": to_bool,
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
    source_row: dict[str, Any],
    column_mappings: list[ColumnMapping]
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
    return db.query(ColumnMapping).filter(
        ColumnMapping.task_id == task_id,
        ColumnMapping.is_active == True
    ).all()


def map_rows(
    source_rows: list[dict[str, Any]],
    column_mappings: list[ColumnMapping]
) -> list[dict[str, Any]]:
    """Map multiple rows from source to destination format"""
    return [map_row_with_column_mappings(row, column_mappings) for row in source_rows]
