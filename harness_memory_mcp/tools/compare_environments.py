from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from core.application.environment_context.use_cases.compare_environments.handler import (
    CompareEnvironmentsHandler,
)
from core.application.environment_context.use_cases.compare_environments.inbound import (
    CompareEnvironmentsInput,
)
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_compare_environments(
    server: FastMCP,
    handler: CompareEnvironmentsHandler,
    tenant_context: TenantContextProvider,
):
    @server.tool(
        name="compare_environments",
        description=(
            "Compare current snapshots between two project environments "
            "(e.g. staging vs production) "
            "to identify added, removed, and unchanged entities. Requires memory:read."
        ),
    )
    def compare_environments(
        project_key: Annotated[str, Field(description="Key of the project to compare.")],
        source_environment: Annotated[
            str, Field(description="Source environment name (e.g. staging).")
        ],
        target_environment: Annotated[
            str, Field(description="Target environment name (e.g. production).")
        ],
        limit: Annotated[
            int,
            Field(ge=1, le=100, description="Maximum entities per list, from 1 to 100."),
        ] = 100,
        offset: Annotated[
            int, Field(ge=0, le=10000, description="Offset for pagination, up to 10000.")
        ] = 0,
        tenant_id: Annotated[str | None, Field(max_length=255,
            description="Select one tenant ID when project keys repeat across tenants.")] = None,
    ):
        try:
            ctx = tenant_context.require_scope("memory:read")
            if tenant_id is not None and not ctx.is_admin and tenant_id != ctx.tenant_id:
                return {"error": {"code": "INVALID_ARGUMENT",
                                  "message": "tenant selector is outside the trusted read scope"}}
            input_data = CompareEnvironmentsInput(
                project_key=project_key,
                source_environment=source_environment,
                target_environment=target_environment,
                tenant_id=tenant_id if ctx.is_admin else ctx.tenant_id,
                limit=limit,
                offset=offset,
            )
            result = handler.execute(input_data)
            return {
                "source_environment": result.source_environment,
                "target_environment": result.target_environment,
                "added_entities": list(result.added_entities),
                "removed_entities": list(result.removed_entities),
                "unchanged_entities": list(result.unchanged_entities),
                "modified_entities": list(result.modified_entities),
                "total_added": result.total_added,
                "total_removed": result.total_removed,
                "total_unchanged": result.total_unchanged,
                "total_modified": result.total_modified,
                **({"source_snapshot_id": str(result.source_snapshot_id)}
                   if result.source_snapshot_id else {}),
                **({"target_snapshot_id": str(result.target_snapshot_id)}
                   if result.target_snapshot_id else {}),
            }
        except Exception as error:
            error_str = str(error).lower()
            if "tenant" in error_str or "scope" in error_str:
                error_code = "MISSING_TENANT_CONTEXT"
                message = "trusted tenant context is required"
            elif isinstance(error, (ValueError, LookupError)):
                error_code = "INVALID_ARGUMENT"
                message = "invalid request parameters"
            else:
                error_code = "INTERNAL_ERROR"
                message = "an internal error occurred while processing the request"
            return {"error": {"code": error_code, "message": message}}

    return compare_environments
