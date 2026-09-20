from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.application.tenant_security.use_cases.record_security_audit.inbound import (
    SecurityAuditCommand,
)
from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord
from core.domain.tenant_security.types import AuditEventType, AuditOutcome, AuditPhase
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


class FakeAuditRepository:
    def __init__(self):
        self.records = []

    def append(self, record):
        self.records.append(record)
        return AppendResult(record.event_id)


def command(**overrides):
    values = {
        "request_id": uuid4(),
        "occurred_at": datetime.now(timezone.utc),
        "event_type": AuditEventType.PUBLICATION,
        "phase": AuditPhase.ATTEMPTED,
        "outcome": AuditOutcome.PENDING,
        "component_kind": "tool",
        "component_name": "publish_project_snapshot",
        "tenant_id": "tenant-a",
        "subject": "subject-a",
        "safe_details": {"project_key": "payments", "revision": "1"},
    }
    values.update(overrides)
    return SecurityAuditCommand(**values)


def test_audit_handler_appends_immutable_allowlisted_record():
    repository = FakeAuditRepository()
    source = {"project_key": "payments"}
    result = RecordSecurityAuditHandler(repository).execute(command(safe_details=source))
    source["project_key"] = "other"

    assert result.persisted is True
    assert result.duplicate is False
    assert repository.records[0].safe_details["project_key"] == "payments"


def test_command_rejects_sensitive_and_unbounded_details():
    with pytest.raises(ValidationError):
        command(safe_details={"token": "secret"})
    with pytest.raises(ValidationError):
        command(safe_details={"project_key": "x" * 256})
    with pytest.raises(ValidationError):
        command(component_name=" ")


def test_record_state_invariants_and_authentication_failure_identity():
    with pytest.raises(ValueError):
        SecurityAuditRecord.create(
            request_id=uuid4(),
            event_type=AuditEventType.PUBLICATION,
            phase=AuditPhase.ATTEMPTED,
            outcome=AuditOutcome.SUCCEEDED,
            component_kind="tool",
            component_name="publish_project_snapshot",
            tenant_id="tenant-a",
            subject="subject-a",
        )
    failure = SecurityAuditRecord.create(
        request_id=uuid4(),
        event_type=AuditEventType.AUTHENTICATION_FAILURE,
        phase=AuditPhase.COMPLETED,
        outcome=AuditOutcome.DENIED,
        component_kind="http",
        component_name="mcp",
        reason_code="invalid_token",
    )
    assert failure.tenant_id is None
    with pytest.raises(ValueError):
        SecurityAuditRecord.create(
            request_id=uuid4(),
            event_type=AuditEventType.PUBLICATION,
            phase=AuditPhase.COMPLETED,
            outcome=AuditOutcome.PENDING,
            component_kind="tool",
            component_name="publish_project_snapshot",
            tenant_id="tenant-a",
            subject="subject-a",
        )


def test_principal_rejects_bad_identity_and_normalizes_scopes():
    principal = AuthenticatedPrincipal(" subject ", " tenant ", frozenset({" memory:read ", ""}))
    assert principal.subject == "subject"
    assert principal.tenant_id == "tenant"
    assert principal.has_scope("memory:read")
    with pytest.raises(ValueError):
        AuthenticatedPrincipal("", "tenant", frozenset())
    with pytest.raises(ValueError):
        AuthenticatedPrincipal("subject", " " * 256, frozenset())
