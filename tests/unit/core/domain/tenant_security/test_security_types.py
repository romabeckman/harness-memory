import pytest

from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.types.audit_outcome import AuditOutcome
from core.domain.tenant_security.types.audit_phase import AuditPhase


def test_authentication_failure_allows_unknown_identity():
    record = SecurityAuditRecord.create(
        request_id="00000000-0000-0000-0000-000000000001",
        event_type=AuditEventType.AUTHENTICATION_FAILURE,
        phase=AuditPhase.COMPLETED,
        outcome=AuditOutcome.DENIED,
        component_kind="http",
        component_name="mcp",
        reason_code="invalid_token",
    )

    assert record.tenant_id is None
    assert record.subject is None


def test_operation_attempt_requires_pending_outcome_and_identity():
    with pytest.raises(ValueError):
        SecurityAuditRecord.create(
            request_id="00000000-0000-0000-0000-000000000001",
            event_type=AuditEventType.PUBLICATION,
            phase=AuditPhase.ATTEMPTED,
            outcome=AuditOutcome.SUCCEEDED,
            component_kind="tool",
            component_name="publish_project_snapshot",
            tenant_id="tenant-a",
            subject="user-a",
        )
