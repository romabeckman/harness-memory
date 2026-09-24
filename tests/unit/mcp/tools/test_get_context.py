from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.get_context import register_get_context


def test_get_context_uses_trusted_tenant_context_and_serializes_result():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = type(
        "Result", (), {"model_dump": lambda self, mode: {"ok": True}}
    )()
    tenant = TenantContextProvider("tenant-a")
    entity_id = uuid4()

    tool = register_get_context(server, handler, tenant)
    result = tool(entity_id=entity_id, result_limit=3, evidence_limit=1)

    assert result == {"ok": True}
    request, scope = handler.execute.call_args.args
    assert request.entity_id == entity_id
    assert request.limit == 100
    assert request.result_limit == 3
    assert scope == TenantScope("tenant-a")


def test_get_context_maps_missing_tenant_context_before_handler_access():
    server = FastMCP(name="test")
    handler = Mock()
    tenant = TenantContextProvider()

    tool = register_get_context(server, handler, tenant)
    result = tool(entity_id=uuid4())

    assert result["error"]["code"] == "MISSING_TENANT_CONTEXT"
    handler.execute.assert_not_called()


def test_get_context_accepts_snapshot_selector_without_entity_id():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = {"items": [], "count": 0, "has_more": False}
    tool = register_get_context(server, handler, TenantContextProvider("tenant-a"))
    snapshot_id = uuid4()

    result = tool(snapshot_id=snapshot_id)

    assert result["items"] == []
    assert handler.execute.call_args.args[0].entity_id is None
    assert handler.execute.call_args.args[0].snapshot_id == snapshot_id
