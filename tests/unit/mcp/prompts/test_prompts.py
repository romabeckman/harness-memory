from unittest.mock import Mock

import pytest
from fastmcp import FastMCP

from harness_memory_mcp.prompts.analyze_integration import register_analyze_integration_prompt
from harness_memory_mcp.prompts.load_corporate_context import register_load_corporate_context_prompt
from harness_memory_mcp.prompts.review_change_impact import register_review_change_impact_prompt

pytestmark = pytest.mark.asyncio


async def test_load_corporate_context_renders_guidance_without_io():
    server = FastMCP(name="test")
    observable = Mock()
    register_load_corporate_context_prompt(server, observable)

    result = await server.render_prompt(
        "load_corporate_context", {"subject": "payments integration"}
    )

    text = str(result)
    assert "search_entities" in text
    assert "search_projects" in text
    assert "query" in text
    assert "get_context" in text
    assert "memory://projects" in text
    assert "exact project key" in text
    assert "If a search is empty" in text
    observable.assert_not_called()


async def test_analyze_integration_renders_workflow_without_computing_path():
    server = FastMCP(name="test")
    observable = Mock()
    register_analyze_integration_prompt(server, observable)

    result = await server.render_prompt(
        "analyze_integration", {"source": "payments-api", "target": "billing-api"}
    )

    text = str(result)
    assert "find_integration_paths" in text
    assert "ownership" in text
    assert "provenance" in text
    observable.assert_not_called()


async def test_review_change_impact_mentions_existing_impact_contract_without_io():
    server = FastMCP(name="test")
    observable = Mock()
    register_review_change_impact_prompt(server, observable)

    result = await server.render_prompt(
        "review_change_impact",
        {"entity_id": "payments-api", "change_type": "contract", "description": "field changed"},
    )

    text = str(result)
    assert "analyze_impact" in text
    assert "unknown" in text
    assert "truncat" in text
    observable.assert_not_called()
