from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastmcp import Client

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def _result(entity_id):
    entity = {
        "id": entity_id,
        "key": "payments",
        "name": "Payments",
        "type": "service",
        "metadata": {},
    }
    return entity


@pytest.mark.asyncio
async def test_relationship_tools_are_catalogued_with_strict_input_fields():
    repository = Mock()
    server = create_mcp_server(
        relationship_repository=repository, tenant_context=TenantContextProvider("tenant-a")
    )

    async with Client(server) as client:
        tools = await client.list_tools()

    names = [tool.name for tool in tools]
    assert names == ["get_context", "get_dependencies"]
    for tool in tools:
        assert "entity_id" in tool.input_schema["properties"]
        assert ("tenant_id" in tool.input_schema["properties"]) == (tool.name == "get_context")
    context_schema = tools[0].input_schema
    assert "entity_id" not in context_schema.get("required", [])
    assert all(
        selector in context_schema["properties"]
        for selector in ("snapshot_id", "project_id", "tenant_id")
    )


@pytest.mark.asyncio
async def test_relationship_tools_return_safe_success_and_validation_results():
    repository = Mock()
    entity_id = uuid4()
    repository.load_context.return_value = {
        "entity": _result(str(entity_id)),
        "project": {
            "key": "payments",
            "name": "Payments",
            "snapshot_id": str(uuid4()),
            "revision": 1,
        },
        "owners": [],
        "relations": [],
        "dependencies": [],
        "relations_truncated": False,
        "dependencies_truncated": False,
    }
    repository.load_dependencies.return_value = {
        "entity": _result(str(entity_id)),
        "items": [],
        "truncated": False,
    }
    server = create_mcp_server(
        relationship_repository=repository, tenant_context=TenantContextProvider("tenant-a")
    )

    async with Client(server) as client:
        context = await client.call_tool("get_context", {"entity_id": str(entity_id)})
        invalid = await client.call_tool(
            "get_dependencies", {"entity_id": "bad"}, raise_on_error=False
        )

    assert context.data["entity"]["id"] == str(entity_id)
    assert invalid.is_error is True


@pytest.mark.asyncio
async def test_relationship_tools_require_read_scope_before_handler_access():
    repository = Mock()
    server = create_mcp_server(
        relationship_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:publish"}),
    )

    async with Client(server) as client:
        context = await client.call_tool("get_context", {"entity_id": str(uuid4())})
        dependencies = await client.call_tool("get_dependencies", {"entity_id": str(uuid4())})

    assert context.data["error"]["code"] == "RELATIONSHIP_UNAUTHORIZED"
    assert dependencies.data["error"]["code"] == "RELATIONSHIP_UNAUTHORIZED"
    repository.load_context.assert_not_called()
    repository.load_dependencies.assert_not_called()


@pytest.mark.parametrize("selector", ["snapshot_id", "project_id", "tenant_id"])
@pytest.mark.asyncio
async def test_get_context_lists_by_scope_selector(selector):
    repository = Mock()
    repository.list_contexts.return_value = {
        "items": [],
        "count": 0,
        "limit": 25,
        "offset": 0,
        "has_more": False,
    }
    server = create_mcp_server(
        relationship_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    value = "tenant-a" if selector == "tenant_id" else str(uuid4())

    async with Client(server) as client:
        result = await client.call_tool("get_context", {selector: value})

    assert result.data["items"] == []
    assert repository.list_contexts.call_args.args[1].entity_id is None
    repository.load_context.assert_not_called()


@pytest.mark.asyncio
async def test_get_context_rejects_missing_selector():
    repository = Mock()
    server = create_mcp_server(
        relationship_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool("get_context", {}, raise_on_error=False)

    assert result.data["error"]["code"] == "INVALID_RELATIONSHIP_CONTRACT"
    repository.load_context.assert_not_called()
    repository.list_contexts.assert_not_called()
