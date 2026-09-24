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
from harness_memory_mcp.services.relationship_response_mapper import RelationshipResponseMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_get_dependencies(
    server: FastMCP,
    handler: GetDependenciesHandler,
    tenant_context: TenantContextProvider,
    response_mapper: RelationshipResponseMapper | None = None,
):
    mapper = response_mapper or RelationshipResponseMapper()

    @server.tool(
        name="get_dependencies",
        description=(
            "Read direct depends_on, consumes, and subscribes_to relationships for an "
            "entity in current project snapshots. Get entity_id from search_entities. "
            "Choose inbound for relationships targeting the entity, outbound for those "
            "starting at it, or both. Returns provenance and bounded evidence. "
            "Requires memory:read."
        ),
    )
    def get_dependencies(
        entity_id: Annotated[
            UUID,
            Field(
                description=(
                    "Entity UUID from search_entities.entity_id; required to read "
                    "direct dependencies."
                )
            ),
        ],
        direction: Annotated[
            RelationshipDirection,
            Field(
                description=(
                    "inbound: relations targeting the entity; outbound: relations "
                    "starting at it; both: both directions (default)."
                )
            ),
        ] = RelationshipDirection.BOTH,
        limit: Annotated[
            StrictInt,
            Field(ge=1, le=100, description="Maximum relationships to return, from 1 to 100."),
        ] = 25,
        evidence_limit: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=20,
                description="Maximum evidence items per relationship, from 0 to 20.",
            ),
        ] = 5,
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            request = GetDependenciesInput(
                entity_id=entity_id,
                direction=direction,
                limit=limit,
                evidence_limit=evidence_limit,
            )
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return get_dependencies
