from uuid import UUID

from core.domain.environment.events.environment_snapshot_promoted import (
    EnvironmentSnapshotPromoted,
)
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.environment.value_objects.environment_type import EnvironmentType
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class Environment:
    id: UUID
    project_key: ProjectKey
    name: EnvironmentName
    environment_type: EnvironmentType
    current_snapshot_id: UUID | None
    _events: list[object]

    def __init__(
        self,
        id: UUID,
        project_key: ProjectKey,
        name: EnvironmentName,
        environment_type: EnvironmentType = EnvironmentType.OTHER,
        current_snapshot_id: UUID | None = None,
    ) -> None:
        self.id = id
        self.project_key = project_key
        self.name = name
        self.environment_type = environment_type
        self.current_snapshot_id = current_snapshot_id
        self._events = []

    @property
    def events(self) -> tuple[object, ...]:
        return tuple(self._events)

    def promote_snapshot(self, snapshot_id: UUID) -> None:
        if not isinstance(snapshot_id, UUID):
            raise ValueError("snapshot_id must be a valid UUID")
        self.current_snapshot_id = snapshot_id
        self._events.append(
            EnvironmentSnapshotPromoted(
                environment_id=self.id,
                project_key=self.project_key.value,
                snapshot_id=snapshot_id,
            )
        )
