from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastmcp import Client

from core.application.impact_analysis.errors.impact_entity_not_found import ImpactEntityNotFound
from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from mcp.server.factory import create_mcp_server
from mcp.services.tenant_context import TenantContextProvider


def _output(entity_id):
    return AnalyzeImpactOutput(
        changed_entity=EntityContextItem(
            id=entity_id,
            key="payments-api",
            name="Payments API",
            type=EntityType.API,
        )
    )


@pytest.mark.asyncio
async def test_impact_tool_is_catalogued_without_untrusted_tenant_input():
    server = create_mcp_server(
        impact_analysis_repository=Mock(),
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:impact"}),
    )

    async with Client(server) as client:
        tools = await client.list_tools()

    tool = next(tool for tool in tools if tool.name == "analyze_impact")
    assert {"entity_id", "change_type", "description"} <= set(tool.input_schema["properties"])
    assert "tenant_id" not in tool.input_schema["properties"]


@pytest.mark.asyncio
async def test_impact_tool_uses_trusted_scope_and_maps_direct_indirect_shape():
    repository = Mock()
    entity_id = uuid4()
    repository.analyze_impact.return_value = _output(entity_id)
    server = create_mcp_server(
        impact_analysis_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:impact"}),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "analyze_impact",
            {"entity_id": str(entity_id), "change_type": "contract"},
        )

    assert result.data["changed_entity"]["id"] == str(entity_id)
    assert result.data["direct_consumers"] == []
    repository.analyze_impact.assert_called_once()
    assert repository.analyze_impact.call_args.args[0].tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_impact_tool_hides_unknown_target_and_rejects_tenant_payload():
    repository = Mock()
    repository.analyze_impact.side_effect = ImpactEntityNotFound("secret")
    server = create_mcp_server(
        impact_analysis_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:impact"}),
    )

    async with Client(server) as client:
        not_found = await client.call_tool(
            "analyze_impact", {"entity_id": str(uuid4())}
        )
        invalid = await client.call_tool(
            "analyze_impact",
            {"entity_id": str(uuid4()), "tenant_id": "tenant-b"},
            raise_on_error=False,
        )

    assert not_found.data["error"]["code"] == "IMPACT_ENTITY_NOT_FOUND"
    assert "secret" not in str(not_found.data)
    assert invalid.is_error is True


@pytest.mark.asyncio
async def test_impact_tool_requires_impact_scope():
    repository = Mock()
    server = create_mcp_server(
        impact_analysis_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:read"}),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "analyze_impact", {"entity_id": str(uuid4())}
        )

    assert result.data["error"]["code"] == "IMPACT_UNAUTHORIZED"
    repository.analyze_impact.assert_not_called()


@pytest.mark.asyncio
async def test_impact_tool_rejects_context_without_explicit_scopes():
    repository = Mock()
    server = create_mcp_server(
        impact_analysis_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "analyze_impact", {"entity_id": str(uuid4())}
        )

    assert result.data["error"]["code"] == "IMPACT_UNAUTHORIZED"
    repository.analyze_impact.assert_not_called()


@pytest.mark.asyncio
async def test_impact_tool_returns_stable_validation_error_for_invalid_bounds():
    repository = Mock()
    server = create_mcp_server(
        impact_analysis_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:impact"}),
    )

    async with Client(server) as client:
        result = await client.call_tool(
            "analyze_impact",
            {"entity_id": str(uuid4()), "max_depth": 0},
            raise_on_error=False,
        )

    assert result.is_error is True
    assert "max_depth" in str(result)
    repository.analyze_impact.assert_not_called()
