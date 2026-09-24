from unittest.mock import Mock

import pytest
from fastmcp import Client, FastMCP

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.publish_project_snapshot import register_publish_project_snapshot


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
        project_search_repository=Mock(),
        relationship_repository=Mock(),
        integration_path_repository=Mock(),
        impact_repository=Mock(),
        get_environment_handler=Mock(),
        compare_environments_handler=Mock(),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        tools = await client.list_tools()

    expected_tools = {
        "search_entities",
        "search_projects",
        "get_context",
        "get_dependencies",
        "find_integration_paths",
        "analyze_impact",
        "get_environment",
        "compare_environments",
    }
    assert {tool.name for tool in tools} == expected_tools

    for tool in tools:
        assert tool.description and tool.description.strip(), tool.name
        for name, definition in _properties(tool.input_schema):
            assert definition.get("description", "").strip(), f"{tool.name}.{name}"


@pytest.mark.asyncio
async def test_catalog_explains_filter_and_identifier_dependencies():
    server = create_mcp_server(
        search_repository=Mock(),
        project_search_repository=Mock(),
        relationship_repository=Mock(),
        integration_path_repository=Mock(),
        impact_repository=Mock(),
        get_environment_handler=Mock(),
        compare_environments_handler=Mock(),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        tools = {tool.name: tool for tool in await client.list_tools()}

    guidance = {
        "search_projects": ("key or query", "at least one"),
        "search_entities": ("at least one filter", "search_projects"),
        "get_context": ("search_entities", "snapshot_id"),
        "get_dependencies": ("search_entities", "depends_on"),
        "find_integration_paths": ("search_entities", "active"),
        "analyze_impact": ("search_entities", "same entity"),
        "get_environment": ("search_projects", "current snapshot"),
        "compare_environments": ("search_projects", "current snapshots"),
    }
    for name, phrases in guidance.items():
        description = tools[name].description.lower()
        for phrase in phrases:
            assert phrase in description, (name, phrase)

    field_guidance = {
        ("search_projects", "key"): "key or query",
        ("search_projects", "query"): "key or query",
        ("search_entities", "request"): "at least one filter",
        ("get_context", "entity_id"): "search_entities",
        ("get_context", "snapshot_id"): "search_entities",
        ("get_dependencies", "direction"): "inbound",
        ("find_integration_paths", "source_entity_id"): "search_entities",
        ("find_integration_paths", "target_entity_id"): "search_entities",
        ("analyze_impact", "change"): "entity_id",
        ("get_environment", "project_key"): "search_projects",
        ("compare_environments", "source_environment"): "get_environment",
    }
    for (tool_name, field_name), phrase in field_guidance.items():
        description = tools[tool_name].input_schema["properties"][field_name]["description"]
        assert phrase in description.lower(), (tool_name, field_name)

    nested = dict(_properties(tools["search_entities"].input_schema))
    assert "unchanged" in nested["cursor"]["description"].lower()
    assert "current snapshot" in nested["environment"]["description"].lower()


@pytest.mark.asyncio
async def test_legacy_publication_tool_describes_complete_payload_and_runtime_status():
    server = FastMCP("legacy-publication")
    register_publish_project_snapshot(
        server, Mock(), TenantContextProvider("tenant-a")
    )

    async with Client(server) as client:
        (tool,) = await client.list_tools()

    assert "not registered" in tool.description.lower()
    assert "rest" in tool.description.lower()
    assert "schema_version" in tool.input_schema["properties"]["request"]["description"]
