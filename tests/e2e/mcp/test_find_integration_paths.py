from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastmcp import Client

from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.application.integration_paths.use_cases.find_integration_paths.outbound import (
    FindIntegrationPathsOutput,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def _output(entity_id):
    entity = EntityContextItem(id=entity_id, key="payments", type=EntityType.SERVICE)
    return FindIntegrationPathsOutput(
        source=entity,
        target=entity,
        paths=(),
        truncated=False,
        termination_reason=PathTerminationReason.COMPLETE,
    )


@pytest.mark.asyncio
async def test_find_integration_paths_is_catalogued_with_bounded_schema():
    repository = Mock()
    server = create_mcp_server(
        integration_path_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    async with Client(server) as client:
        tools = await client.list_tools()
    path_tool = next(tool for tool in tools if tool.name == "find_integration_paths")
    properties = path_tool.input_schema["properties"]
    assert {"source_entity_id", "target_entity_id"} <= set(properties)
    assert "tenant_id" not in properties
    assert properties["max_depth"]["minimum"] == 1
    assert properties["max_depth"]["maximum"] == 8


@pytest.mark.asyncio
async def test_find_integration_paths_uses_trusted_context_and_maps_success():
    repository = Mock()
    entity_id = uuid4()
    repository.find_paths.return_value = _output(entity_id)
    server = create_mcp_server(
        integration_path_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "find_integration_paths",
            {"source_entity_id": str(entity_id), "target_entity_id": str(entity_id)},
        )
    assert result.data["termination_reason"] == "complete"
    repository.find_paths.assert_called_once()
    assert repository.find_paths.call_args.args[0].tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_find_integration_paths_hides_not_found_and_rejects_tenant_input():
    repository = Mock()
    repository.find_paths.side_effect = IntegrationPathEndpointNotFound("secret")
    server = create_mcp_server(
        integration_path_repository=repository,
        tenant_context=TenantContextProvider("tenant-a"),
    )
    async with Client(server) as client:
        not_found = await client.call_tool(
            "find_integration_paths",
            {"source_entity_id": str(uuid4()), "target_entity_id": str(uuid4())},
        )
        invalid = await client.call_tool(
            "find_integration_paths",
            {
                "source_entity_id": str(uuid4()),
                "target_entity_id": str(uuid4()),
                "tenant_id": "tenant-b",
            },
            raise_on_error=False,
        )
    assert not_found.data["error"]["code"] == "INTEGRATION_PATH_ENDPOINT_NOT_FOUND"
    assert "secret" not in str(not_found.data)
    assert invalid.is_error is True


@pytest.mark.asyncio
async def test_find_integration_paths_fails_before_repository_when_context_missing():
    repository = Mock()
    server = create_mcp_server(
        integration_path_repository=repository,
        tenant_context=TenantContextProvider(),
    )
    async with Client(server) as client:
        result = await client.call_tool(
            "find_integration_paths",
            {"source_entity_id": str(uuid4()), "target_entity_id": str(uuid4())},
        )
    assert result.data["error"]["code"] == "MISSING_TENANT_CONTEXT"
    repository.find_paths.assert_not_called()

