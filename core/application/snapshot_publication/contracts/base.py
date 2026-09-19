import json
from datetime import datetime, timezone
from typing import Any


def validate_metadata(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("metadata root must be a JSON object")
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    if len(encoded) > 64 * 1024:
        raise ValueError("metadata exceeds 64 KiB")
    return value


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must include a UTC offset")
    return value.astimezone(timezone.utc)


def trim_bounded(value: str | None, field_name: str, maximum: int) -> str | None:
    if value is None:
        return None
    trimmed = value.strip()
    if not 1 <= len(trimmed) <= maximum:
        raise ValueError(f"{field_name} must contain 1 to {maximum} characters")
    return trimmed
