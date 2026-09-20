import pytest
from fastmcp import Client

from harness_memory_mcp.server.factory import create_mcp_server


@pytest.mark.asyncio
async def test_f007_prompts_render_fixed_guidance_without_data_access():
    server = create_mcp_server()

    async with Client(server) as client:
        context = await client.get_prompt(
            "load_corporate_context", {"subject": "review payments"}
        )
        integration = await client.get_prompt(
            "analyze_integration", {"source": "payments", "target": "billing"}
        )
        impact = await client.get_prompt(
            "review_change_impact",
            {"entity_id": "payments-api", "change_type": "contract"},
        )

    assert "search_entities" in str(context)
    assert "find_integration_paths" in str(integration)
    assert "analyze_impact" in str(impact)

