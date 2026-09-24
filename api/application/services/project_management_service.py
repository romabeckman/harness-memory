from typing import Any
from uuid import UUID

from api.application.ports.tenant_project_management_repository import (
    TenantProjectManagementRepository,
)


class ProjectManagementService:
    def __init__(self, repository: TenantProjectManagementRepository) -> None:
        self._repository = repository

    def create(
        self, tenant_id: UUID, key: str, name: str | None, metadata: dict[str, Any]
    ) -> dict:
        return self._repository.create_project(tenant_id, key, name, metadata)

    def get(self, tenant_id: UUID, key: str) -> dict:
        project = self._repository.get_project(tenant_id, key)
        if project is None:
            raise LookupError("project not found")
        return project

    def list(
        self,
        tenant_id: UUID | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        return self._repository.list_projects(
            tenant_id=tenant_id, query=query, limit=limit, offset=offset
        )

    def update(self, tenant_id: UUID, key: str, values: dict[str, Any]) -> dict:
        project = self._repository.update_project(tenant_id, key, values)
        if project is None:
            raise LookupError("project not found")
        return project

    def delete(self, tenant_id: UUID, key: str) -> None:
        if not self._repository.delete_project(tenant_id, key):
            raise LookupError("project not found")
