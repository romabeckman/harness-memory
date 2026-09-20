from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Revision:
    value: int

    def __post_init__(self) -> None:
        if isinstance(self.value, bool) or not isinstance(self.value, int) or self.value < 1:
            raise ValueError("revision must be a positive integer")
