from typing import Any
from uuid import UUID

from api.application.ports.tenant_project_management_repository import (
    TenantProjectManagementRepository,
)


class TenantManagementService:
    def __init__(self, repository: TenantProjectManagementRepository) -> None:
        self._repository = repository

    def create(self, key: str, name: str, metadata: dict[str, Any]) -> dict:
        return self._repository.create_tenant(key, name, metadata)

    def get(self, tenant_id: UUID) -> dict:
        tenant = self._repository.get_tenant(tenant_id)
        if tenant is None:
            raise LookupError("tenant not found")
        return tenant

    def list(
        self,
        query: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        return self._repository.list_tenants(
            query=query, status=status, limit=limit, offset=offset
        )

    def update(self, tenant_id: UUID, values: dict[str, Any]) -> dict:
        tenant = self._repository.update_tenant(tenant_id, values)
        if tenant is None:
            raise LookupError("tenant not found")
        return tenant

    def delete(self, tenant_id: UUID) -> None:
        if self._repository.get_tenant(tenant_id) is None:
            raise LookupError("tenant not found")
        if not self._repository.delete_tenant(tenant_id):
            raise LookupError("tenant not found")
