from unittest.mock import Mock

import pytest
from fastmcp import Client

from core.application.entity_discovery.contracts.project_search_item import ProjectSearchItem
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_search_projects_returns_bounded_project_references_and_uses_tenant_scope():
    repository = Mock()
    repository.search_projects.return_value = [
        ProjectSearchItem(key="send", name="Send", has_active_snapshot=True)
    ]
    server = create_mcp_server(
        project_search_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", {"key": "send"})

    assert result.data == {
        "items": [{"key": "send", "name": "Send", "has_active_snapshot": True}],
        "count": 1,
        "limit": 25,
        "offset": 0,
        "has_more": False,
    }
    repository.search_projects.assert_called_once_with(
        TenantScope("tenant-a"), key="send", query=None, limit=26, offset=0
    )


@pytest.mark.asyncio
async def test_search_projects_supports_name_or_key_query_and_offset_pages():
    repository = Mock()
    repository.search_projects.return_value = [
        ProjectSearchItem(key="send", name="Send", has_active_snapshot=False),
        ProjectSearchItem(key="sender", name="Sender", has_active_snapshot=True),
    ]
    server = create_mcp_server(
        project_search_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "search_projects", {"query": "send", "limit": 1, "offset": 1}
        )

    assert result.data["items"] == [
        {"key": "send", "name": "Send", "has_active_snapshot": False}
    ]
    assert result.data["offset"] == 1
    assert result.data["has_more"] is True
    repository.search_projects.assert_called_once_with(
        TenantScope("tenant-a"), key=None, query="send", limit=2, offset=1
    )


@pytest.mark.parametrize("arguments", [{}, {"key": None, "query": None, "limit": 25, "offset": 0}])
@pytest.mark.asyncio
async def test_search_projects_lists_projects_without_filters(arguments):
    repository = Mock()
    repository.search_projects.return_value = [
        ProjectSearchItem(key="send", name="Send", has_active_snapshot=False)
    ]
    server = create_mcp_server(
        project_search_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", arguments)

    assert result.data["items"][0]["key"] == "send"
    repository.search_projects.assert_called_once_with(
        TenantScope("tenant-a"), key=None, query=None, limit=26, offset=0
    )


@pytest.mark.parametrize("arguments", [{"key": "  "}, {"query": "  "}])
@pytest.mark.asyncio
async def test_search_projects_rejects_blank_filters(arguments):
    repository = Mock()
    server = create_mcp_server(
        project_search_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "search_projects", arguments, raise_on_error=False
        )

    assert result.data["error"]["code"] == "INVALID_ARGUMENT"
    repository.search_projects.assert_not_called()


@pytest.mark.asyncio
async def test_search_projects_requires_memory_read_before_querying_repository():
    repository = Mock()
    server = create_mcp_server(
        project_search_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes=["memory:publish"]),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", {"key": "send"})

    assert result.data["error"]["code"] == "READ_UNAUTHORIZED"
    repository.search_projects.assert_not_called()
