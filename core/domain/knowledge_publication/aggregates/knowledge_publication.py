from uuid import UUID

from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.knowledge_publication.events.knowledge_publication_recorded import (
    KnowledgePublicationRecorded,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId
from core.domain.knowledge_publication.value_objects.publication_id import PublicationId
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class KnowledgePublication:
    id: PublicationId
    project_key: ProjectKey
    environment_name: EnvironmentName
    deployment_id: DeploymentId
    version: str
    status: PublicationStatus
    snapshot_id: UUID | None
    _events: list[object]

    def __init__(
        self,
        id: PublicationId,
        project_key: ProjectKey,
        environment_name: EnvironmentName,
        deployment_id: DeploymentId,
        version: str,
        status: PublicationStatus = PublicationStatus.PENDING,
        snapshot_id: UUID | None = None,
    ) -> None:
        self.id = id
        self.project_key = project_key
        self.environment_name = environment_name
        self.deployment_id = deployment_id
        self.version = version
        self.status = status
        self.snapshot_id = snapshot_id
        self._events = []

    @property
    def events(self) -> tuple[object, ...]:
        return tuple(self._events)

    def complete(self, snapshot_id: UUID) -> None:
        if self.status == PublicationStatus.COMPLETED:
            raise ValueError("publication is already completed")
        if not isinstance(snapshot_id, UUID):
            raise ValueError("snapshot_id must be a valid UUID")
        self.snapshot_id = snapshot_id
        self.status = PublicationStatus.COMPLETED
        self._events.append(
            KnowledgePublicationRecorded(
                publication_id=self.id.value,
                snapshot_id=snapshot_id,
                environment_name=self.environment_name.value,
                deployment_id=self.deployment_id.value,
            )
        )
