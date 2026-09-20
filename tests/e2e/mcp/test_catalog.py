import pytest

from mcp.config import RuntimeSettings
from mcp.server.factory import create_mcp_server

pytestmark = pytest.mark.asyncio


async def test_mcp_catalog_exposes_guidance_prompts_without_read_handlers():
    fastmcp = pytest.importorskip("fastmcp")
    Client = fastmcp.Client
    server = create_mcp_server(RuntimeSettings(mcp_host="127.0.0.1", mcp_port=8000))

    async with Client(server) as client:
        tools = await client.list_tools()
        resources = await client.list_resources()
        prompts = await client.list_prompts()

    assert server.name == "harness-memory"
    assert tools == []
    assert resources == []
    assert {prompt.name for prompt in prompts} == {
        "load_corporate_context",
        "analyze_integration",
        "review_change_impact",
    }
