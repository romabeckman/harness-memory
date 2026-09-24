from typing import Annotated

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
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
            "Find entities in active project snapshots by default. Set "
            "include_past_snapshots to search older snapshots as well. Each match "
            "identifies its snapshot, environment, and publication version when known. "
            "Confirm the project "
            "with search_projects when its key is unknown. A request with at least one "
            "filter or tenant/project/snapshot/environment selector is required. Combine "
            "filters to narrow results; use next_cursor with unchanged filters for later "
            "pages. Results include entity_id, project_id, and snapshot_id for context "
            "reads. Requires memory:read."
        ),
    )
    def search_entities(
        request: Annotated[
            SearchEntitiesInput,
            Field(
                description=(
                    "Required request object. Supply at least one filter or "
                    "tenant/project/snapshot/environment selector; include_history, "
                    "include_past_snapshots, limit, and cursor alone do not qualify. "
                    "Use unchanged filters "
                    "with a continuation cursor."
                )
            ),
        ],
    ):
        if all(
            value is None
            for value in (
                request.key,
                request.name,
                request.type,
                request.project,
                request.query,
                request.tenant_id,
                request.project_id,
                request.snapshot_id,
                request.environment,
            )
        ):
            raise ToolError("INVALID_ARGUMENT: at least one discovery filter is required")

        try:
            context = tenant_context.require_scope("memory:read")
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return search_entities
