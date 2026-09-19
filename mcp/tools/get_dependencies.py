from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.use_cases.get_dependencies.handler import (
    GetDependenciesHandler,
)
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from mcp.services.relationship_response_mapper import RelationshipResponseMapper
from mcp.services.tenant_context import TenantContextProvider


def register_get_dependencies(
    server: FastMCP,
    handler: GetDependenciesHandler,
    tenant_context: TenantContextProvider,
    response_mapper: RelationshipResponseMapper | None = None,
):
    mapper = response_mapper or RelationshipResponseMapper()

    @server.tool(name="get_dependencies")
    def get_dependencies(
        entity_id: UUID,
        direction: RelationshipDirection = RelationshipDirection.BOTH,
        limit: Annotated[StrictInt, Field(ge=1, le=100)] = 25,
        evidence_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
    ):
        try:
            context = tenant_context.require()
            request = GetDependenciesInput(
                entity_id=entity_id,
                direction=direction,
                limit=limit,
                evidence_limit=evidence_limit,
            )
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return get_dependencies
