from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class EntityKey:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip() if isinstance(self.value, str) else ""
        if not 1 <= len(value) <= 255:
            raise ValueError("entity key must contain 1 to 255 characters")
        object.__setattr__(self, "value", value)
