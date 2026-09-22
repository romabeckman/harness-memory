from uuid import UUID

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.use_cases.get_snapshot_resource.handler import (
    GetSnapshotResourceHandler,
)
from harness_memory_mcp.services.resource_error_mapper import ResourceErrorMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_snapshot_resource(
    server: FastMCP,
    handler: GetSnapshotResourceHandler,
    tenant_context: TenantContextProvider,
    response_mapper: ResourceErrorMapper | None = None,
):
    mapper = response_mapper or ResourceErrorMapper()

    @server.resource(
        "memory://snapshots/{snapshot_id}",
        name="snapshot_memory",
        description="Bounded facts from a tenant-owned snapshot.",
        mime_type="application/json",
    )
    def snapshot_resource(snapshot_id: UUID):
        try:
            context = tenant_context.require_scope("memory:read")
            request = SnapshotResourceInput(snapshot_id=snapshot_id)
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return snapshot_resource
