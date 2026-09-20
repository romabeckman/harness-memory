import re
from dataclasses import dataclass


@dataclass(frozen=True)
class EnvironmentName:
    value: str

    def __post_init__(self) -> None:
        trimmed = self.value.strip()
        if not trimmed:
            raise ValueError("environment name must not be empty")
        if len(self.value) > 64:
            raise ValueError("environment name exceeds maximum length")
        if not re.match(r"^[a-zA-Z0-9_\-]+$", self.value):
            raise ValueError("environment name contains invalid characters")
