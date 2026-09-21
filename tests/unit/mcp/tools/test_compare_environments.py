from unittest.mock import Mock

from fastmcp import FastMCP

from core.application.environment_context.use_cases.compare_environments.outbound import (
    CompareEnvironmentsOutput,
)
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.compare_environments import register_compare_environments


def test_compare_environments_returns_structural_diff() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.return_value = CompareEnvironmentsOutput(
        source_environment="staging",
        target_environment="production",
        added_entities=("POST /products/v2",),
        removed_entities=("POST /products/v1",),
        unchanged_entities=("GET /products",),
        total_added=1,
        total_removed=1,
        total_unchanged=1,
    )
    tenant = TenantContextProvider("tenant-a")

    tool = register_compare_environments(server, handler, tenant)
    result = tool(
        project_key="catalog",
        source_environment="staging",
        target_environment="production",
    )

    assert result["source_environment"] == "staging"
    assert result["target_environment"] == "production"
    assert result["added_entities"] == ["POST /products/v2"]
    assert result["removed_entities"] == ["POST /products/v1"]
    assert result["unchanged_entities"] == ["GET /products"]
    assert result["total_added"] == 1
    assert handler.execute.call_args[0][0].tenant_id == "tenant-a"


def test_compare_environments_maps_missing_tenant_context() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    tenant = TenantContextProvider()

    tool = register_compare_environments(server, handler, tenant)
    result = tool(
        project_key="catalog",
        source_environment="staging",
        target_environment="production",
    )

    assert result["error"]["code"] == "MISSING_TENANT_CONTEXT"
    handler.execute.assert_not_called()


def test_compare_environments_sanitizes_internal_error() -> None:
    server = FastMCP(name="test")
    handler = Mock()
    handler.execute.side_effect = RuntimeError("database secret password leaked at host 10.0.0.1")
    tenant = TenantContextProvider("tenant-a")

    tool = register_compare_environments(server, handler, tenant)
    result = tool(
        project_key="catalog",
        source_environment="staging",
        target_environment="production",
    )

    assert result["error"]["code"] == "INTERNAL_ERROR"
    assert "password" not in result["error"]["message"]
    assert result["error"]["message"] == "an internal error occurred while processing the request"
