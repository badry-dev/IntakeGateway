from collections.abc import Iterable
from typing import Any

from jsonpath_ng.ext import parse as jsonpath_parse


def select_records(payload: Any, record_path: str | None) -> Iterable[dict]:
    if record_path:
        jp = jsonpath_parse(record_path)
        matches = [m.value for m in jp.find(payload)]
        # A path that resolves to exactly one scalar (not a list/dict) is most
        # likely a misconfigured record_path pointing at a string or number field
        # rather than an array. Catch it early rather than silently wrapping the
        # scalar in a list and producing downstream type errors.
        if len(matches) == 1 and not isinstance(matches[0], (list, dict)):
            raise ValueError(f"Record path '{record_path}' did not resolve to a list or object")
        # If the path resolved to a list-of-lists (e.g. $.items), unwrap one level.
        if len(matches) == 1 and isinstance(matches[0], list):
            matches = matches[0]
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
