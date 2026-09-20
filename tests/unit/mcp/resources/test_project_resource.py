from unittest.mock import Mock

from fastmcp import FastMCP

from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from mcp.resources.project_resource import register_project_resource
from mcp.services.tenant_context import TenantContextProvider


def test_project_resource_decodes_percent_encoded_key_once():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = type(
        "Result", (), {"model_dump": lambda self, mode: {"ok": True}}
    )()
    resource = register_project_resource(
        server, handler, TenantContextProvider("tenant-a", scopes={"memory:read"})
    )

    result = resource("github.com%2Fcompany%2Fpayments-api")

    assert result == {"ok": True}
    request, scope = handler.execute.call_args.args
    assert request == ProjectResourceInput(project_key="github.com/company/payments-api")
    assert scope.tenant_id == "tenant-a"


def test_project_resource_maps_missing_and_foreign_resources_to_same_error():
    server = FastMCP(name="test")
    handler = Mock()
    from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound

    handler.execute.side_effect = ResourceNotFound("internal tenant detail")
    resource = register_project_resource(
        server, handler, TenantContextProvider("tenant-a", scopes={"memory:read"})
    )

    result = resource("missing")

    assert result["error"] == {
        "code": "RESOURCE_NOT_FOUND",
        "message": "memory resource not found",
    }
    assert "tenant" not in str(result).lower()
