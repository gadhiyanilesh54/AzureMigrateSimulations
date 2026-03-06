"""Request validation helpers for the Flask API.

Provides reusable functions to validate and sanitise incoming JSON payloads,
returning clear error messages when constraints are violated.
"""

from __future__ import annotations

from typing import Any


def require_fields(body: dict[str, Any], fields: list[str]) -> str | None:
    """Return an error message if any *fields* are missing or blank in *body*.

    Works for string fields (checks ``strip()``), numbers, bools, etc.
    Returns ``None`` when all required fields are present and non-blank.
    """
    missing = []
    for f in fields:
        val = body.get(f)
        if val is None:
            missing.append(f)
        elif isinstance(val, str) and not val.strip():
            missing.append(f)
    if missing:
        return f"Missing required field(s): {', '.join(missing)}"
    return None


def validate_int(
    body: dict[str, Any],
    key: str,
    default: int,
    *,
    lo: int | None = None,
    hi: int | None = None,
) -> tuple[int, str | None]:
    """Extract an integer from *body[key]* with optional range clamping.

    Returns ``(value, error_message)``.  If the key is absent the *default* is
    used.  If the raw value cannot be converted to ``int`` an error string is
    returned.
    """
    raw = body.get(key, default)
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default, f"'{key}' must be an integer, got {raw!r}"
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value, None


def validate_choice(
    body: dict[str, Any],
    key: str,
    choices: set[str] | list[str],
    default: str,
) -> tuple[str, str | None]:
    """Extract a string value that must be one of *choices*.

    Returns ``(value, error_message)``.
    """
    val = body.get(key, default)
    if not isinstance(val, str):
        return default, f"'{key}' must be a string"
    if val not in choices:
        allowed = ", ".join(sorted(choices))
        return default, f"Invalid {key} '{val}'. Allowed: {allowed}"
    return val, None
