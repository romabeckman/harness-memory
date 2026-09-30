from unittest.mock import Mock

import pytest
from fastmcp import Client

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_history_query_round_trip_and_scope_validation():
    handler = Mock()
    handler.execute.return_value = {"snapshots": [], "total_snapshots": 0, "has_more": False}
    server = create_mcp_server(
        get_history_handler=handler,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "get_history",
            {
                "project_key": "catalog",
                "environment": "production",
                "query": "authentication",
                "limit": 500,
            },
        )
        invalid = await client.call_tool(
            "get_history",
            {
                "project_key": "catalog",
                "environment": "production",
                "query": " ",
            },
        )
    assert result.data["total_snapshots"] == 0
    assert handler.execute.call_args.args[0].query == "authentication"
    assert handler.execute.call_args.args[0].limit == 500
    assert handler.execute.call_args.args[0].tenant_id == "tenant-a"
    assert invalid.data["error"]["code"] == "INVALID_ARGUMENT"
    assert handler.execute.call_count == 1
