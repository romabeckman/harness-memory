from unittest.mock import Mock

import pytest
from fastmcp import Client

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def _properties(schema):
    if isinstance(schema, dict):
        yield from schema.get("properties", {}).items()
        for value in schema.values():
            yield from _properties(value)
    elif isinstance(schema, list):
        for value in schema:
            yield from _properties(value)


@pytest.mark.asyncio
async def test_all_registered_tools_and_arguments_have_descriptions():
    server = create_mcp_server(
        handler=Mock(),
        search_repository=Mock(),
        relationship_repository=Mock(),
        integration_path_repository=Mock(),
        impact_repository=Mock(),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        tools = await client.list_tools()

    expected_tools = {
        "publish_project_snapshot",
        "search_entities",
        "get_context",
        "get_dependencies",
        "find_integration_paths",
        "analyze_impact",
    }
    assert {tool.name for tool in tools} == expected_tools

    for tool in tools:
        assert tool.description and tool.description.strip(), tool.name
        for name, definition in _properties(tool.input_schema):
            assert definition.get("description", "").strip(), f"{tool.name}.{name}"
