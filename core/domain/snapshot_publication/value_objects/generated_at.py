from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True, slots=True)
class GeneratedAt:
    value: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.value, datetime) or self.value.tzinfo is None:
            raise ValueError("generated_at must include a UTC offset")
        object.__setattr__(self, "value", self.value.astimezone(timezone.utc))
