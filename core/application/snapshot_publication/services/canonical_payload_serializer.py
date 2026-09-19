import json
from datetime import datetime, timezone
from typing import Any


def _normalize(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = value.astimezone(timezone.utc)
        return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")
    if isinstance(value, dict):
        return {key: _normalize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalize(item) for item in value]
    return value


class CanonicalPayloadSerializer:
    def serialize(self, payload: Any) -> bytes:
        data = payload.model_dump(mode="python") if hasattr(payload, "model_dump") else payload
        normalized = _normalize(data)
        return json.dumps(
            normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
