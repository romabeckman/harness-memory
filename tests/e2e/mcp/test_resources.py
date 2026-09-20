from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastmcp import Client

from mcp.server.factory import create_mcp_server
from mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_entity_resource_returns_json_for_read_scope():
    repository = Mock()
    entity_id = uuid4()
    repository.load_context.return_value = {
        "entity": {"id": str(entity_id), "key": "payments-api", "type": "api", "metadata": {}},
        "project": {
            "key": "payments",
            "snapshot_id": str(uuid4()),
            "revision": 1,
        },
        "owners": [],
        "relations": [],
        "dependencies": [],
        "relations_truncated": False,
        "dependencies_truncated": False,
    }
    server = create_mcp_server(
        relationship_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:read"}),
    )

    async with Client(server) as client:
        contents = await client.read_resource(f"memory://entities/{entity_id}")

    assert len(contents) == 1
    assert contents[0].mimeType == "application/json"
    assert "payments-api" in contents[0].text


@pytest.mark.asyncio
async def test_resources_reject_missing_read_scope_before_repository_access():
    repository = Mock()
    server = create_mcp_server(
        relationship_repository=repository,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:impact"}),
    )

    async with Client(server) as client:
        result = await client.read_resource(f"memory://entities/{uuid4()}")

    assert "RESOURCE_UNAUTHORIZED" in result[0].text
    repository.load_context.assert_not_called()


@pytest.mark.asyncio
async def test_project_resource_decodes_encoded_slash_once_in_process():
    handler = Mock()
    handler.execute.return_value = {
        "project": {"key": "github.com/company/payments-api"},
        "entities": [],
        "entities_truncated": False,
    }
    server = create_mcp_server(
        project_resource_handler=handler,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:read"}),
    )

    async with Client(server) as client:
        contents = await client.read_resource(
            "memory://projects/github.com%2Fcompany%2Fpayments-api"
        )

    assert "github.com/company/payments-api" in contents[0].text
    assert handler.execute.call_args.args[0].project_key == "github.com/company/payments-api"


@pytest.mark.asyncio
async def test_snapshot_resource_reads_historical_contract_in_process():
    handler = Mock()
    snapshot_id = uuid4()
    handler.execute.return_value = {
        "snapshot": {
            "id": str(snapshot_id),
            "project_key": "payments",
            "revision": 1,
            "schema_version": "1.0",
        },
        "facts": {
            "entities": [],
            "relations": [],
            "evidence": [],
            "entities_truncated": False,
            "relations_truncated": False,
            "evidence_truncated": False,
        },
    }
    server = create_mcp_server(
        snapshot_resource_handler=handler,
        tenant_context=TenantContextProvider("tenant-a", scopes={"memory:read"}),
    )

    async with Client(server) as client:
        contents = await client.read_resource(f"memory://snapshots/{snapshot_id}")

    assert str(snapshot_id) in contents[0].text
    assert handler.execute.call_args.args[0].snapshot_id == snapshot_id
