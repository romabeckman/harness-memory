from typing import Protocol
from uuid import UUID

from core.domain.knowledge_publication.aggregates.knowledge_publication import (
    KnowledgePublication,
)
from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)


class KnowledgePublicationRepository(Protocol):
    def find_by_deployment(
        self, project_key: str, env_name: str, deployment_id: str, tenant_id: str
    ) -> KnowledgePublication | None:
        ...

    def save(self, publication: KnowledgePublication, tenant_id: str) -> None:
        ...

    def publish_atomically_with_environment(
        self,
        tenant_id: str,
        publication: KnowledgePublication,
        snapshot: ProjectKnowledgeSnapshot,
        environment_id: UUID,
    ) -> UUID:
        ...
