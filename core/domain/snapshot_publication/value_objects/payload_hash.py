import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PayloadHash:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or re.fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ValueError("payload hash must be lowercase SHA-256 hexadecimal")
