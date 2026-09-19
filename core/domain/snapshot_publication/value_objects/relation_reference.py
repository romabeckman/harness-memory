from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RelationReference:
    value: str

    def __post_init__(self) -> None:
        value = self.value.strip() if isinstance(self.value, str) else ""
        if not 1 <= len(value) <= 255:
            raise ValueError("relation reference must contain 1 to 255 characters")
        object.__setattr__(self, "value", value)
