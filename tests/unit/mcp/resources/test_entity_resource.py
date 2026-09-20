from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from mcp.resources.entity_resource import register_entity_resource
from mcp.services.tenant_context import TenantContextProvider


def test_entity_resource_requires_read_scope_before_handler_access():
    server = FastMCP(name="test")
    handler = Mock()
    resource = register_entity_resource(
        server, handler, TenantContextProvider("tenant-a", scopes={"memory:impact"})
    )

    result = resource(uuid4())

    assert result["error"]["code"] == "RESOURCE_UNAUTHORIZED"
    handler.execute.assert_not_called()


def test_entity_resource_delegates_with_active_context_bounds():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = type(
        "Result", (), {"model_dump": lambda self, mode: {"ok": True}}
    )()
    tenant = TenantContextProvider("tenant-a", scopes={"memory:read"})
    entity_id = uuid4()
    resource = register_entity_resource(server, handler, tenant)

    result = resource(entity_id)

    assert result == {"ok": True}
    request, scope = handler.execute.call_args.args
    assert request == GetContextInput(entity_id=entity_id, limit=25, evidence_limit=5)
    assert scope == TenantScope("tenant-a")
