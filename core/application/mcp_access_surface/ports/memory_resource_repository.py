from typing import Protocol

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.application.mcp_access_surface.use_cases.get_project_resource.outbound import (
    ProjectResourceOutput,
)
from core.application.mcp_access_surface.use_cases.get_snapshot_resource.outbound import (
    SnapshotResourceOutput,
)


class MemoryResourceRepository(Protocol):
    def load_active_project(
        self,
        request: ProjectResourceInput,
        tenant: TenantScope,
        bounds: ResourceReadBounds,
    ) -> ProjectResourceOutput: ...

    def load_snapshot(
        self,
        request: SnapshotResourceInput,
        tenant: TenantScope,
        bounds: ResourceReadBounds,
    ) -> SnapshotResourceOutput: ...
