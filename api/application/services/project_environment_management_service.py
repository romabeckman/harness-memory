from uuid import UUID

from core.application.environment_context.ports.environment_repository import (
    EnvironmentRepository,
)


class ProjectEnvironmentManagementService:
    def __init__(self, repository: EnvironmentRepository) -> None:
        self._repository = repository

    def create(self, tenant_id: UUID, project_key: str, name: str) -> dict[str, str]:
        environment = self._repository.create_for_project(str(tenant_id), project_key, name)
        return {
            "id": str(environment.id),
            "tenant_id": str(tenant_id),
            "project_key": project_key,
            "name": environment.name.value,
            "type": environment.environment_type.value,
        }
