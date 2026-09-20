import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest

from core.application.tenant_security.use_cases.record_security_audit.inbound import (
    SecurityAuditCommand,
)
from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord
from core.domain.tenant_security.types import AuditEventType, AuditOutcome, AuditPhase
from core.domain.tenant_security.value_objects.authenticated_principal import (
    AuthenticatedPrincipal,
)
from harness_memory_mcp.server.http_security import install_http_security_error_mapping
from harness_memory_mcp.services.authenticated_principal_factory import (
    AuthenticatedPrincipalFactory,
)
from harness_memory_mcp.services.authorization_failure import AuthorizationFailure
from harness_memory_mcp.services.component_scope_policy import ComponentScopePolicy
from harness_memory_mcp.services.request_security_context import RequestSecurityContext
from harness_memory_mcp.services.security_failure_mapper import SecurityFailureMapper


def test_domain_record_normalizes_identifiers_and_accepts_command_mapping():
    command = SecurityAuditCommand(
        request_id=uuid4(),
        occurred_at=datetime.now(timezone.utc),
        event_type=AuditEventType.AUTHENTICATION_FAILURE,
        phase=AuditPhase.COMPLETED,
        outcome=AuditOutcome.DENIED,
        component_kind="http",
        component_name="mcp",
    )
    record = SecurityAuditRecord.from_command(command)
    assert record.request_id == command.request_id
    with pytest.raises(ValueError):
        SecurityAuditRecord(
            event_id="bad",
            request_id=uuid4(),
            occurred_at=datetime.now(timezone.utc),
            event_type=AuditEventType.AUTHENTICATION_FAILURE,
            phase=AuditPhase.COMPLETED,
            outcome=AuditOutcome.DENIED,
            component_kind="http",
            component_name="mcp",
        )


def test_command_validates_event_identity_and_state():
    with pytest.raises(ValueError):
        SecurityAuditCommand(
            event_type=AuditEventType.AUTHORIZATION_FAILURE,
            phase=AuditPhase.COMPLETED,
            outcome=AuditOutcome.DENIED,
            component_kind="tool",
            component_name="search_entities",
        )


def test_context_bind_supports_async_callables_and_factory_rejects_bad_claims():
    context = RequestSecurityContext()
    principal = AuthenticatedPrincipal("subject", "tenant", frozenset())

    async def call_next():
        await asyncio.sleep(0)
        return context.require().tenant_id

    assert asyncio.run(context.bind(principal, call_next)) == "tenant"
    assert context.current() is None
    factory = AuthenticatedPrincipalFactory()
    with pytest.raises(ValueError):
        factory.from_verified_claims(None)


def test_policy_uri_matching_and_failure_mapping():
    policy = ComponentScopePolicy()
    principal = AuthenticatedPrincipal("subject", "tenant", frozenset({"memory:read"}))
    assert policy.can_access(principal, "resource", "memory://entities/abc")
    assert not policy.can_access(principal, "resource", "memory://entities/abc/extra")
    mapped = SecurityFailureMapper().map(AuthorizationFailure(required_scope="memory:read"))
    assert mapped.status_code == 403


def test_authentication_failure_mapping_always_uses_stable_invalid_token_code():
    mapped = SecurityFailureMapper().authentication("database connection failed")

    assert mapped.status_code == 401
    assert mapped.code == "invalid_token"
    assert mapped.message == "authentication required"
    assert mapped.headers == {"WWW-Authenticate": 'Bearer error="invalid_token"'}


def test_http_security_mapping_changes_only_authorization_errors():
    async def original(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send(
            {
                "type": "http.response.body",
                "body": b'{"isError":true,"text":"Authorization failed"}',
            }
        )

    server = SimpleNamespace(http_app=lambda: original)
    install_http_security_error_mapping(server)
    messages = []

    async def send(message):
        messages.append(message)

    asyncio.run(server.http_app()({"type": "http"}, None, send))
    assert messages[0]["status"] == 403
    assert (b"www-authenticate", b'Bearer error="insufficient_scope"') in messages[0]["headers"]
