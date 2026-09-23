from collections.abc import Mapping

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.ports.memory_resource_repository import (
    MemoryResourceRepository,
)
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class GetProjectResourceHandler:
    def __init__(self, repository: MemoryResourceRepository):
        self._repository = repository

    def execute(
        self,
        request: ProjectResourceInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ):
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        scope = (
            tenant_scope
            if isinstance(tenant_scope, TenantScope)
            else TenantScope(getattr(tenant_scope, "tenant_id", ""),
                             getattr(tenant_scope, "is_admin", False))
        )
        input_model = (
            request
            if isinstance(request, ProjectResourceInput)
            else ProjectResourceInput.model_validate(request)
        )
        return self._repository.load_active_project(input_model, scope, ResourceReadBounds())


GetProjectResource = GetProjectResourceHandler
