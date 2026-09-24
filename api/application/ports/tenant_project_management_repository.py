from typing import Any, Protocol
from uuid import UUID


class TenantProjectManagementRepository(Protocol):
    def create_tenant(self, key: str, name: str, metadata: dict[str, Any]) -> dict: ...

    def get_tenant(self, tenant_id: UUID) -> dict | None: ...

    def list_tenants(
        self,
        query: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict: ...

    def update_tenant(self, tenant_id: UUID, values: dict[str, Any]) -> dict | None: ...

    def delete_tenant(self, tenant_id: UUID) -> bool: ...

    def create_project(
        self, tenant_id: UUID, key: str, name: str | None, metadata: dict[str, Any]
    ) -> dict: ...

    def get_project(self, tenant_id: UUID, key: str) -> dict | None: ...

    def list_projects(
        self,
        tenant_id: UUID | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict: ...

    def update_project(
        self, tenant_id: UUID, key: str, values: dict[str, Any]
    ) -> dict | None: ...

    def delete_project(self, tenant_id: UUID, key: str) -> bool: ...
