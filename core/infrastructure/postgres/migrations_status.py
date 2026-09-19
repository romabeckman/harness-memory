from dataclasses import dataclass


@dataclass(frozen=True)
class MigrationStatus:
    current_revision: str | None
    head_revision: str

    @property
    def is_current(self) -> bool:
        return self.current_revision == self.head_revision
