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
from mcp.services.integration_path_response_mapper import IntegrationPathResponseMapper
from mcp.services.tenant_context import TenantContextProvider


def register_find_integration_paths(
    server: FastMCP,
    handler: FindIntegrationPathsHandler,
    tenant_context: TenantContextProvider,
    response_mapper: IntegrationPathResponseMapper | None = None,
):
    mapper = response_mapper or IntegrationPathResponseMapper()

    @server.tool(name="find_integration_paths")
    def find_integration_paths(
        source_entity_id: UUID,
        target_entity_id: UUID,
        max_depth: Annotated[StrictInt, Field(ge=1, le=8)] = 4,
        max_paths: Annotated[StrictInt, Field(ge=1, le=25)] = 10,
        evidence_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
        owner_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
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
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return find_integration_paths
