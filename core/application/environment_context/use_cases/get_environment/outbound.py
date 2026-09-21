from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class GetEnvironmentOutput:
    found: bool
    environment_id: UUID | None = None
    environment_name: str | None = None
    environment_type: str | None = None
    current_snapshot_id: UUID | None = None
