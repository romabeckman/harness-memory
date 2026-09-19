from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SchemaVersion:
    value: str

    def __post_init__(self) -> None:
        if self.value != "1.0":
            raise ValueError("unsupported snapshot schema version")
