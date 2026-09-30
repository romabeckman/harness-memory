from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.get_dependencies import register_get_dependencies


def test_get_dependencies_accepts_direction_and_uses_trusted_scope():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = type(
        "Result", (), {"model_dump": lambda self, mode: {"ok": True}}
    )()
    tenant = TenantContextProvider("tenant-a")
    entity_id = uuid4()

    tool = register_get_dependencies(server, handler, tenant)
    result = tool(entity_id=entity_id, direction=RelationshipDirection.INBOUND)

    assert result == {"ok": True}
    request, scope = handler.execute.call_args.args
    assert request.direction is RelationshipDirection.INBOUND
    assert request.limit == 100
    assert scope == TenantScope("tenant-a")
