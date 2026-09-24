from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field

from core.application.environment_context.use_cases.get_environment.handler import (
    GetEnvironmentHandler,
)
from core.application.environment_context.use_cases.get_environment.inbound import (
    GetEnvironmentInput,
)
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_get_environment(
    server: FastMCP,
    handler: GetEnvironmentHandler,
    tenant_context: TenantContextProvider,
):
    @server.tool(
        name="get_environment",
        description=(
            "Retrieve metadata, type, and current snapshot ID for a named environment "
            "in a project. Requires memory:read."
        ),
    )
    def get_environment(
        project_key: Annotated[str, Field(description="Key of the project to inspect.")],
        environment: Annotated[
            str,
            Field(description="Environment name, such as development, staging, or production."),
        ],
        tenant_id: Annotated[str | None, Field(max_length=255,
            description="Select one tenant ID when project keys repeat across tenants.")] = None,
    ):
        try:
            ctx = tenant_context.require_scope("memory:read")
            if tenant_id is not None and not ctx.is_admin and tenant_id != ctx.tenant_id:
                return {"error": {"code": "INVALID_ARGUMENT",
                                  "message": "tenant selector is outside the trusted read scope"}}
            input_data = GetEnvironmentInput(
                project_key=project_key,
                environment_name=environment,
                tenant_id=tenant_id if ctx.is_admin else ctx.tenant_id,
            )
            result = handler.execute(input_data)
            return {
                "found": result.found,
                "environment_id": str(result.environment_id) if result.environment_id else None,
                "environment_name": result.environment_name,
                "environment_type": result.environment_type,
                "current_snapshot_id": str(result.current_snapshot_id)
                if result.current_snapshot_id
                else None,
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

    return get_environment
