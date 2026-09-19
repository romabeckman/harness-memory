from typing import Protocol

from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.value_objects.payload_hash import PayloadHash

from ..types.publication_record import PublicationRecord


class SnapshotPublicationStore(Protocol):
    def publish_atomically(
        self, tenant_id: str, snapshot: ProjectKnowledgeSnapshot, payload_hash: PayloadHash
    ) -> PublicationRecord: ...
