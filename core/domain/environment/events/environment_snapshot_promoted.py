from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class EnvironmentSnapshotPromoted:
    environment_id: UUID
    project_key: str
    snapshot_id: UUID
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
