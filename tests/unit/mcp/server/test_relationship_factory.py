from unittest.mock import Mock

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def test_factory_accepts_one_relationship_repository_for_both_handlers():
    repository = Mock()

    server = create_mcp_server(
        relationship_repository=repository, tenant_context=TenantContextProvider("tenant-a")
    )

    assert server.name == "harness-memory"
