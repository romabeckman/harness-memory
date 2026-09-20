from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from core.application.environment_context.use_cases.get_environment.outbound import (
    GetEnvironmentOutput,
)
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.get_environment import register_get_environment


def test_get_environment_returns_environment_details() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    env_id = uuid4()
    snap_id = uuid4()
    handler.execute.return_value = GetEnvironmentOutput(
        found=True,
        environment_id=env_id,
        environment_name="staging",
        environment_type="staging",
        current_snapshot_id=snap_id,
    )
    tenant = TenantContextProvider("tenant-a")

    tool = register_get_environment(server, handler, tenant)
    result = tool(project_key="catalog", environment="staging")

    assert result["found"] is True
    assert result["environment_name"] == "staging"
    assert result["current_snapshot_id"] == str(snap_id)
    assert handler.execute.call_args[0][0].tenant_id == "tenant-a"


def test_get_environment_maps_missing_tenant_context() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    tenant = TenantContextProvider()

    tool = register_get_environment(server, handler, tenant)
    result = tool(project_key="catalog", environment="staging")

    assert result["error"]["code"] == "MISSING_TENANT_CONTEXT"
    handler.execute.assert_not_called()


def test_get_environment_sanitizes_internal_error() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.side_effect = RuntimeError("database secret password leaked at host 10.0.0.1")
    tenant = TenantContextProvider("tenant-a")

    tool = register_get_environment(server, handler, tenant)
    result = tool(project_key="catalog", environment="staging")

    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "password" not in result["error"]["message"]
    assert result["error"]["message"] == "an internal error occurred while processing the request"
