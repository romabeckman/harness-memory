from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.types.integration_path_bounds import IntegrationPathBounds
from core.application.integration_paths.use_cases.find_integration_paths.handler import (
    FindIntegrationPathsHandler,
)
from core.application.integration_paths.use_cases.find_integration_paths.inbound import (
    FindIntegrationPathsInput,
)
from harness_memory_mcp.services.integration_path_response_mapper import (
    IntegrationPathResponseMapper,
)
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_find_integration_paths(
    server: FastMCP,
    handler: FindIntegrationPathsHandler,
    tenant_context: TenantContextProvider,
    response_mapper: IntegrationPathResponseMapper | None = None,
):
    mapper = response_mapper or IntegrationPathResponseMapper()

    @server.tool(
        name="find_integration_paths",
        description=(
            "Find bounded integration paths between two entities in active project "
            "snapshots. Get both entity IDs from search_entities. Traversal uses "
            "provides, consumes, depends_on, publishes, subscribes_to, and implements "
            "relations; paths include direction, provenance, evidence, and ownership. "
            "Requires memory:read."
        ),
    )
    def find_integration_paths(
        source_entity_id: Annotated[
            UUID,
            Field(
                description=(
                    "Starting entity UUID from search_entities.entity_id; "
                    "required endpoint in an active snapshot."
                )
            ),
        ],
        target_entity_id: Annotated[
            UUID,
            Field(
                description=(
                    "Destination entity UUID from search_entities.entity_id; "
                    "required endpoint in an active snapshot."
                )
            ),
        ],
        max_depth: Annotated[
            StrictInt,
            Field(ge=1, le=8, description="Maximum relationship hops per path, from 1 to 8."),
        ] = 4,
        max_paths: Annotated[
            StrictInt,
            Field(ge=1, le=25, description="Maximum paths to return, from 1 to 25."),
        ] = 10,
        evidence_limit: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=20,
                description="Maximum evidence items per relationship, from 0 to 20.",
            ),
        ] = 5,
        owner_limit: Annotated[
            StrictInt,
            Field(ge=0, le=20, description="Maximum owner records per entity, from 0 to 20."),
        ] = 5,
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            request = FindIntegrationPathsInput(
                source_entity_id=source_entity_id,
                target_entity_id=target_entity_id,
                bounds=IntegrationPathBounds(
                    max_depth=max_depth,
                    max_paths=max_paths,
                    evidence_limit=evidence_limit,
                    owner_limit=owner_limit,
                ),
            )
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return find_integration_paths
