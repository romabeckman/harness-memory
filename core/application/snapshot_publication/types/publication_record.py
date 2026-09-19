from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class PublicationRecord:
    status: str
    snapshot_id: UUID
    requested_revision: int
    stored_revision: int
    active_snapshot_id: UUID
    payload_hash: str
    entity_count: int
    relation_count: int
    evidence_count: int
