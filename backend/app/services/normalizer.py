from typing import Any, Iterable
from jsonpath_ng.ext import parse as jsonpath_parse


def select_records(payload: Any, record_path: str | None) -> Iterable[dict]:
    if record_path:
        jp = jsonpath_parse(record_path)
        found = [m.value for m in jp.find(payload)]
        # Unwrap single match so the value (not the wrapper list) is type-checked
        matches = found[0] if len(found) == 1 else found
    else:
        matches = payload
    if isinstance(matches, dict):
        matches = [matches]
    if not isinstance(matches, list):
        raise ValueError("Record path did not resolve to a list or object")
    return matches


def flatten(obj: dict | Any, parent_key: str = "", sep: str = ".") -> dict:
    """
    Flatten a nested dictionary structure.
    If obj is a primitive (int, str, float, bool), wrap it in a dict with key 'value'.
    """
    # Handle primitive types by wrapping in a dict
    if not isinstance(obj, dict):
        return {"value": obj}

    items = []
    for k, v in obj.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
