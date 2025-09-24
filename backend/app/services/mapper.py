
from typing import Any, Callable

# Minimal transform registry for MVP
def trim(x): 
    return x.strip() if isinstance(x, str) else x
def upper(x):
    return x.upper() if isinstance(x, str) else x
TRANSFORMS: dict[str, Callable[[Any], Any]] = {
    "trim": trim,
    "upper": upper,
}

def apply_transform(value: Any, transform: str | None):
    if not transform:
        return value
    fn = TRANSFORMS.get(transform)
    if not fn:
        raise ValueError(f"Unknown transform: {transform}")
    return fn(value)
