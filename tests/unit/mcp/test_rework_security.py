import asyncio
import time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.domain.tenant_security.value_objects.authenticated_principal import (
    AuthenticatedPrincipal,
)
from harness_memory_mcp.config import RuntimeSettings, SecuritySettings
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.server.http_security import install_http_security_error_mapping
from harness_memory_mcp.services.audited_operation import ExecuteAuditedOperation
from harness_memory_mcp.services.security_audit_middleware import AuditingTokenVerifier


class RecordingRepository:
    def __init__(self, fail_on_append=False):
        self.records = []
        self.fail_on_append = fail_on_append

    def append(self, record):
        if self.fail_on_append and len(self.records) >= 1:
            raise RuntimeError("database unavailable")
        self.records.append(record)
        return AppendResult(record.event_id)


def _principal():
    return AuthenticatedPrincipal("subject-a", "tenant-a", frozenset({"memory:publish"}))


def _production_settings(require_auth=True):
    return RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/.well-known/jwks.json",
        mcp_audience="harness-memory",
        mcp_require_auth=require_auth,
    )


def test_production_security_urls_require_https():
    with pytest.raises(ValidationError):
        SecuritySettings(
            issuer="http://issuer.example",
            jwks_uri="https://issuer.example/jwks",
            audience="harness-memory",
        )
    with pytest.raises(ValidationError):
        RuntimeSettings(
            mcp_issuer="https://issuer.example",
            mcp_jwks_uri="http://issuer.example/jwks",
            mcp_audience="harness-memory",
            mcp_production=True,
        )


def test_failed_completion_has_bounded_reason_code():
    repository = RecordingRepository()
    audited = ExecuteAuditedOperation(RecordSecurityAuditHandler(repository))

    with pytest.raises(ValueError):
        audited.execute(
            operation=lambda: (_ for _ in ()).throw(ValueError("unsafe details")),
            principal=_principal(),
            request_id=uuid4(),
            event_type="publication",
            component="publish_project_snapshot",
            required_scope="memory:publish",
        )

    assert repository.records[-1].reason_code == "value_error"


def test_operation_error_survives_completion_audit_failure():
    repository = RecordingRepository(fail_on_append=True)
    audited = ExecuteAuditedOperation(RecordSecurityAuditHandler(repository))

    with pytest.raises(ValueError, match="business failure"):
        audited.execute(
            operation=lambda: (_ for _ in ()).throw(ValueError("business failure")),
            principal=_principal(),
            request_id=uuid4(),
            event_type="impact_analysis",
            component="analyze_impact",
            required_scope="memory:impact",
        )


def test_invalid_token_audit_runs_without_blocking_event_loop():
    audit_done = False

    def append(_command):
        nonlocal audit_done
        time.sleep(0.04)
        audit_done = True
        return SimpleNamespace(event_id=uuid4())

    async def verify_token(_token):
        return None

    verifier = AuditingTokenVerifier(
        SimpleNamespace(verify_token=verify_token),
        SimpleNamespace(execute=append),
    )
    observed_during_audit = False

    async def ticker():
        nonlocal observed_during_audit
        await asyncio.sleep(0.005)
        observed_during_audit = not audit_done

    async def run():
        await asyncio.gather(verifier.verify_token("bad"), ticker())

    asyncio.run(run())
    assert observed_during_audit


def test_require_auth_builds_authenticated_production_composition():
    async def verify_token(_token):
        return None

    handler = SimpleNamespace(execute=lambda _command: SimpleNamespace(event_id=uuid4()))
    server = create_mcp_server(
        settings=_production_settings(),
        token_verifier=SimpleNamespace(verify_token=verify_token),
        audit_handler=handler,
    )

    assert any(type(middleware).__name__ == "AuthMiddleware" for middleware in server.middleware)
    assert any(
        type(middleware).__name__ == "SecurityAuditMiddleware" for middleware in server.middleware
    )


def test_production_jwt_verifier_does_not_emit_claim_values():
    handler = SimpleNamespace(execute=lambda _command: SimpleNamespace(event_id=uuid4()))
    server = create_mcp_server(
        settings=RuntimeSettings(
            mcp_issuer="https://issuer.example",
            mcp_jwks_uri="https://issuer.example/jwks",
            mcp_audience="harness-memory",
            mcp_production=True,
        ),
        audit_handler=handler,
    )

    assert server.auth.verifier.logger.disabled is True


def test_http_security_mapping_preserves_streaming_chunks():
    first_forwarded = False
    messages = []

    async def original(scope, receive, send):
        nonlocal first_forwarded
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/event-stream")],
            }
        )
        await send({"type": "http.response.body", "body": b"first", "more_body": True})
        first_forwarded = bool(messages)
        await send({"type": "http.response.body", "body": b"second", "more_body": False})

    server = SimpleNamespace(http_app=lambda: original)
    install_http_security_error_mapping(server)

    async def send(message):
        messages.append(message)

    asyncio.run(server.http_app()({"type": "http"}, None, send))
    assert first_forwarded
    assert [
        message.get("body") for message in messages if message["type"] == "http.response.body"
    ] == [
        b"first",
        b"second",
    ]


def test_imported_asgi_server_fails_closed_without_production_configuration():
    import harness_memory_mcp.server.app as app

    with TestClient(app.server) as client:
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
    assert response.status_code != 200
