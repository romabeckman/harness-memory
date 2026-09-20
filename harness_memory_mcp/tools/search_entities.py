from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.use_cases.search_entities.handler import (
    SearchEntitiesHandler,
)
from core.application.entity_discovery.use_cases.search_entities.inbound import SearchEntitiesInput
from harness_memory_mcp.services.entity_search_response_mapper import EntitySearchResponseMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_search_entities(
    server: FastMCP,
    handler: SearchEntitiesHandler,
    tenant_context: TenantContextProvider,
    response_mapper: EntitySearchResponseMapper | None = None,
):
    mapper = response_mapper or EntitySearchResponseMapper()

    @server.tool(
        name="search_entities",
        description=(
            "Find tenant-visible entities by key, name, type, or project. "
            "Results are paginated and bounded. Requires memory:read."
        ),
    )
    def search_entities(
        request: Annotated[
            SearchEntitiesInput,
            Field(description="Entity filters, page size, and optional continuation cursor."),
        ],
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return search_entities
