from unittest.mock import Mock

from mcp.server.factory import create_mcp_server
from mcp.services.tenant_context import TenantContextProvider


def test_factory_path_handler_receives_trusted_scope_and_request_without_tenant_field():
    repository = Mock()
    server = create_mcp_server(
        integration_path_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    assert server.name == "harness-memory"

