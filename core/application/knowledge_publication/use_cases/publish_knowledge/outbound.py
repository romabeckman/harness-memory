from dataclasses import dataclass
from uuid import UUID

from core.domain.knowledge_publication.types.publication_status import PublicationStatus


@dataclass(frozen=True)
class PublishKnowledgeOutput:
    publication_id: UUID
    snapshot_id: UUID
    status: PublicationStatus
