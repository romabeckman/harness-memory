from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4
import pytest
from starlette.testclient import TestClient
from fastmcp.server.auth import AccessToken, TokenVerifier

from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.infrastructure.telemetry.telemetry_tracer import TelemetryTracer
from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.trace_context_holder import TraceContextHolder


class StaticTokenVerifier(TokenVerifier):
    async def verify_token(self, token):
        if token != "valid-token":
            return None
        return AccessToken(
            token=token,
            client_id="subject-1",
            scopes=["memory:impact", "memory:read"],
            subject="subject-1",
            claims={
                "sub": "subject-1",
                "tenant_id": "tenant-test",
                "scope": "memory:impact memory:read",
            },
        )


def test_correlate_traceparent_with_security_audit_record():
    records = []
    repository = SimpleNamespace(
        append=lambda record: records.append(record) or AppendResult(record.event_id)
    )
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/.well-known/jwks.json",
        mcp_audience="harness-memory",
        mcp_production=True,
    )
    mock_handler = MagicMock()
    entity_id = uuid4()
    mock_handler.execute.return_value = AnalyzeImpactOutput(
        changed_entity=EntityContextItem(
            id=entity_id,
            key="test-service",
            name="Test Service",
            type=EntityType.SERVICE,
        )
    )
    server = create_mcp_server(
        settings=settings,
        production=True,
        verify_schema=False,
        token_verifier=StaticTokenVerifier(),
        audit_repository=repository,
        impact_handler=mock_handler,
    )

    traceparent = "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    headers = {
        "Authorization": "Bearer valid-token",
        "traceparent": traceparent,
    }

    with TestClient(server.http_app()) as client:
        # Initialize MCP session
        init_res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0"},
                },
            },
            headers=headers,
        )
        assert init_res.status_code == 200
        session_id = init_res.headers["mcp-session-id"]
        headers["Mcp-Session-Id"] = session_id

        # Call audited impact analysis tool
        call_res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "analyze_impact",
                    "arguments": {"entity_id": str(entity_id)},
                },
            },
            headers=headers,
        )
        assert call_res.status_code == 200

    # Verify audit record captured trace_id
    impact_records = [r for r in records if r.event_type == AuditEventType.IMPACT_ANALYSIS]
    assert len(impact_records) >= 1
    assert "trace_id" in impact_records[0].safe_details
    assert impact_records[0].safe_details["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert impact_records[0].safe_details["span_id"] == "00f067aa0ba902b7"


def test_tool_execution_succeeds_when_telemetry_exporter_fails():
    failing_tracer = MagicMock(spec=TelemetryTracer)
    failing_tracer.start_as_current_span.side_effect = RuntimeError("exporter timeout")

    server = create_mcp_server(
        production=False,
        verify_schema=False,
        telemetry_tracer=failing_tracer,
    )

    with TestClient(server.http_app()) as client:
        # Initialize
        init_res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "t", "version": "1"},
                },
            },
        )
        session_id = init_res.headers["mcp-session-id"]
        headers = {"Mcp-Session-Id": session_id}

        # Tool call succeeds despite telemetry failure
        res = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "search_entities", "arguments": {"query": "test"}},
            },
            headers=headers,
        )
        assert res.status_code == 200
