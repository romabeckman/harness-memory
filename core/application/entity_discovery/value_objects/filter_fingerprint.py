import hashlib
import json
import re
from dataclasses import dataclass

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)


@dataclass(frozen=True, slots=True)
class FilterFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not re.fullmatch(r"[0-9a-f]{64}", self.value):
            raise ValueError("invalid filter fingerprint")

    @classmethod
    def from_criteria(cls, criteria: EntitySearchCriteria) -> "FilterFingerprint":
        payload = {
            "key": criteria.key,
            "name": criteria.name,
            "type": criteria.type.value if criteria.type is not None else None,
            "project": criteria.project,
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return cls(hashlib.sha256(encoded).hexdigest())
