import pytest
from fastmcp import Client

from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_f007_catalog_exposes_three_resource_templates_and_three_prompts():
    server = create_mcp_server(
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:read"}),
        get_context_handler=object(),
        project_resource_handler=object(),
        snapshot_resource_handler=object(),
    )

    async with Client(server) as client:
        resources = await client.list_resource_templates()
        prompts = await client.list_prompts()

    assert {resource.uriTemplate for resource in resources} >= {
        "memory://entities/{entity_id}",
        "memory://projects/{project_key}",
        "memory://snapshots/{snapshot_id}",
    }
    assert {prompt.name for prompt in prompts} >= {
        "load_corporate_context",
        "analyze_integration",
        "review_change_impact",
    }
