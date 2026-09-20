import re
from urllib.parse import unquote

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.use_cases.get_project_resource.handler import (
    GetProjectResourceHandler,
)
from mcp.services.resource_error_mapper import ResourceErrorMapper
from mcp.services.tenant_context import TenantContextProvider

_INVALID_PERCENT_ESCAPE = re.compile(r"%(?![0-9a-fA-F]{2})")


def register_project_resource(
    server: FastMCP,
    handler: GetProjectResourceHandler,
    tenant_context: TenantContextProvider,
    response_mapper: ResourceErrorMapper | None = None,
):
    mapper = response_mapper or ResourceErrorMapper()

    @server.resource(
        "memory://projects/{project_key}",
        name="project_memory",
        description="Bounded facts from a project's active snapshot.",
        mime_type="application/json",
    )
    def project_resource(project_key: str):
        try:
            if _INVALID_PERCENT_ESCAPE.search(project_key):
                raise ValueError("invalid project key encoding")
            decoded_key = unquote(project_key)
            request = ProjectResourceInput(project_key=decoded_key)
            context = tenant_context.require_scope("memory:read")
            result = handler.execute(request, TenantScope(context.tenant_id))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return project_resource
