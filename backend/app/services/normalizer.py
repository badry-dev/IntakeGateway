
from typing import Any, Iterable
from jsonpath_ng.ext import parse as jsonpath_parse

def select_records(payload: Any, record_path: str | None) -> Iterable[dict]:
    if record_path:
        jp = jsonpath_parse(record_path)
        matches = [m.value for m in jp.find(payload)]
    else:
        matches = payload
    if isinstance(matches, dict):
        matches = [matches]
    if not isinstance(matches, list):
        raise ValueError("Record path did not resolve to a list or object")
    return matches

def flatten(obj: dict, parent_key: str = "", sep: str = ".") -> dict:
    items = []
    for k, v in obj.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
