from uuid import UUID

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.use_cases.get_context.handler import GetContextHandler
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from mcp.services.resource_error_mapper import ResourceErrorMapper
from mcp.services.tenant_context import TenantContextProvider


def register_entity_resource(
    server: FastMCP,
    handler: GetContextHandler,
    tenant_context: TenantContextProvider,
    response_mapper: ResourceErrorMapper | None = None,
):
    mapper = response_mapper or ResourceErrorMapper()

    @server.resource(
        "memory://entities/{entity_id}",
        name="entity_memory",
        description="Bounded active-snapshot entity context.",
        mime_type="application/json",
    )
    def entity_resource(entity_id: UUID):
        try:
            context = tenant_context.require_scope("memory:read")
            request = GetContextInput(entity_id=entity_id, limit=25, evidence_limit=5)
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return entity_resource
