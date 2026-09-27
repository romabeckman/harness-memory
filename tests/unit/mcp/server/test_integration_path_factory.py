from unittest.mock import Mock

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def test_factory_registers_configured_integration_path_repository():
    server = create_mcp_server(
        integration_path_repository=Mock(),
        tenant_context=TenantContextProvider("tenant-a"),
    )
    assert server.name == "harness-memory"
