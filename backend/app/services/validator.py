
from typing import Any

def validate_row(row: dict[str, Any], column_specs: list[dict]) -> list[str]:
    errors: list[str] = []
    for col in column_specs:
        name = col["dest_column"]
        nullable = col.get("nullable", True)
        v = row.get(name)
        if v is None and not nullable:
            errors.append(f"Column {name} is required") 
    return errors
