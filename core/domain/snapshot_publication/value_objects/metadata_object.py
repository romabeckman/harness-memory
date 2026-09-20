import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    if isinstance(value, tuple):
        return tuple(_freeze(item) for item in value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise ValueError("metadata must contain JSON-serializable values")


def thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [thaw(item) for item in value]
    return value


@dataclass(frozen=True, slots=True)
class MetadataObject:
    value: Mapping[str, Any]

    def __init__(self, value: Mapping[str, Any] | None = None):
        if value is None:
            value = {}
        if not isinstance(value, dict):
            raise ValueError("metadata root must be a JSON object")
        frozen = _freeze(value)
        if (
            len(
                json.dumps(
                    thaw(frozen), sort_keys=True, separators=(",", ":"), ensure_ascii=False
                ).encode("utf-8")
            )
            > 64 * 1024
        ):
            raise ValueError("metadata exceeds 64 KiB")
        object.__setattr__(self, "value", frozen)

    def to_dict(self) -> dict[str, Any]:
        return thaw(self.value)
