from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from mcp.resources.snapshot_resource import register_snapshot_resource
from mcp.services.tenant_context import TenantContextProvider


def test_snapshot_resource_passes_uuid_to_handler():
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = type(
        "Result", (), {"model_dump": lambda self, mode: {"ok": True}}
    )()
    snapshot_id = uuid4()
    resource = register_snapshot_resource(
        server, handler, TenantContextProvider("tenant-a", scopes={"memory:read"})
    )

    result = resource(snapshot_id)

    assert result == {"ok": True}
    request, scope = handler.execute.call_args.args
    assert request == SnapshotResourceInput(snapshot_id=snapshot_id)
    assert scope.tenant_id == "tenant-a"
