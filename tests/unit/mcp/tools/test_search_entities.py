from unittest.mock import Mock

import pytest
from fastmcp import Client

from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.use_cases.search_entities.handler import (
    SearchEntitiesHandler,
)
from mcp.server.factory import create_mcp_server
from mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_search_tool_delegates_and_maps_success():
    repository = Mock()
    repository.search.return_value = EntitySearchPage(items=(), limit=25)
    server = create_mcp_server(
        search_handler=SearchEntitiesHandler(repository),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_entities", {"request": {"key": "payments"}})

    assert result.data == {"items": [], "count": 0, "next_cursor": None}


@pytest.mark.asyncio
async def test_search_tool_is_registered_and_returns_stable_empty_success():
    repository = Mock()
    repository.search.return_value = EntitySearchPage(items=(), limit=25)
    server = create_mcp_server(
        search_handler=SearchEntitiesHandler(repository),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        tools = await client.list_tools()
        result = await client.call_tool("search_entities", {"request": {"key": "payments"}})

    assert [tool.name for tool in tools] == ["search_entities"]
    assert result.data == {"items": [], "count": 0, "next_cursor": None}
    repository.search.assert_called_once()


@pytest.mark.asyncio
async def test_search_tool_sanitizes_failures_and_rejects_missing_context():
    repository = Mock()
    repository.search.side_effect = RuntimeError("SQL password=secret tenant-a /private/path")
    server = create_mcp_server(
        search_handler=SearchEntitiesHandler(repository),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_entities", {"request": {"key": "payments"}})

    assert result.data["error"]["code"] == "SEARCH_FAILED"
    assert "secret" not in str(result.data)

    no_context = create_mcp_server(
        search_handler=SearchEntitiesHandler(Mock()), tenant_context=TenantContextProvider()
    )
    async with Client(no_context) as client:
        result = await client.call_tool("search_entities", {"request": {"key": "payments"}})
    assert result.data["error"]["code"] == "MISSING_TENANT_CONTEXT"
