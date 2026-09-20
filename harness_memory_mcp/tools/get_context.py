from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.use_cases.get_context.handler import GetContextHandler
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from harness_memory_mcp.services.relationship_response_mapper import RelationshipResponseMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_get_context(
    server: FastMCP,
    handler: GetContextHandler,
    tenant_context: TenantContextProvider,
    response_mapper: RelationshipResponseMapper | None = None,
):
    mapper = response_mapper or RelationshipResponseMapper()

    @server.tool(name="get_context")
    def get_context(
        entity_id: UUID,
        limit: Annotated[StrictInt, Field(ge=1, le=100)] = 25,
        evidence_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            request = GetContextInput(
                entity_id=entity_id, limit=limit, evidence_limit=evidence_limit
            )
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return get_context
