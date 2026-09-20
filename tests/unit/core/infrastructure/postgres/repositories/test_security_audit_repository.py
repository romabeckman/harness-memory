from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord
from core.domain.tenant_security.types import AuditEventType, AuditOutcome, AuditPhase
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.security_audit_event import SecurityAuditEvent
from core.infrastructure.postgres.repositories.security_audit_repository import (
    PostgresSecurityAuditRepository,
)


def record():
    return SecurityAuditRecord.create(
        request_id="00000000-0000-0000-0000-000000000010",
        event_type=AuditEventType.AUTHENTICATION_FAILURE,
        phase=AuditPhase.COMPLETED,
        outcome=AuditOutcome.DENIED,
        component_kind="http",
        component_name="mcp",
        reason_code="invalid_token",
    )


def test_append_is_idempotent_and_preserves_nullable_identity():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    repository = PostgresSecurityAuditRepository(engine=engine)
    first = repository.append(record())
    second = repository.append(record())

    assert first.persisted is True
    assert second.duplicate is True
    with Session(engine) as session:
        row = session.execute(select(SecurityAuditEvent)).scalar_one()
        assert row.tenant_id is None
        assert row.subject is None
