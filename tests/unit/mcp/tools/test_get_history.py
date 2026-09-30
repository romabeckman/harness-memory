from unittest.mock import Mock
from uuid import uuid4

from fastmcp import FastMCP

from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.get_history import register_get_history


def test_get_history_scopes_request_to_authenticated_tenant():
    handler = Mock()
    handler.execute.return_value = {"snapshots": []}
    tool = register_get_history(FastMCP("test"), handler, TenantContextProvider("tenant-a"))

    assert tool("catalog", "production") == {"snapshots": []}
    assert handler.execute.call_args.args[0].tenant_id == "tenant-a"
    assert (
        tool("catalog", "production", tenant_id="tenant-b")["error"]["code"] == "INVALID_ARGUMENT"
    )
    assert handler.execute.call_count == 1


def test_get_history_sanitizes_failure_and_rejects_invalid_bounds():
    handler = Mock()
    handler.execute.side_effect = RuntimeError("password leaked")
    tool = register_get_history(FastMCP("test"), handler, TenantContextProvider("tenant-a"))

    assert tool("catalog", "production", snapshot_id=uuid4())["error"] == {
        "code": "INTERNAL_ERROR",
        "message": "history read failed",
    }
    assert tool("catalog", "production", limit=0)["error"]["code"] == "INVALID_ARGUMENT"


def test_get_history_reports_missing_trusted_context():
    handler = Mock()
    tool = register_get_history(FastMCP("test"), handler, TenantContextProvider())

    assert tool("catalog", "production")["error"] == {
        "code": "MISSING_TENANT_CONTEXT",
        "message": "trusted tenant context is required",
    }
    handler.execute.assert_not_called()


def test_get_history_forwards_query_and_rejects_blank_terms():
    handler = Mock()
    handler.execute.return_value = {"snapshots": []}
    tool = register_get_history(FastMCP("test"), handler, TenantContextProvider("tenant-a"))
    assert tool("catalog", "production", query="authentication") == {"snapshots": []}
    assert handler.execute.call_args.args[0].query == "authentication"
    assert tool("catalog", "production", query=" ")["error"]["code"] == "INVALID_ARGUMENT"
