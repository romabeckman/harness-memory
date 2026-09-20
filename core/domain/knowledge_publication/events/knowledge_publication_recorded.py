from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID


@dataclass(frozen=True)
class KnowledgePublicationRecorded:
    publication_id: UUID
    snapshot_id: UUID
    environment_name: str
    deployment_id: str
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
