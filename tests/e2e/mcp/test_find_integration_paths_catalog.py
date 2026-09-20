from unittest.mock import Mock

import pytest
from fastmcp import Client

from mcp.server.factory import create_mcp_server
from mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_path_tool_is_registered_once_when_configured():
    server = create_mcp_server(
        integration_path_repository=Mock(),
        tenant_context=TenantContextProvider("tenant-a"),
    )
    async with Client(server) as client:
        tools = await client.list_tools()
    assert [tool.name for tool in tools].count("find_integration_paths") == 1

