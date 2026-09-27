from collections.abc import Callable

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord

from ..models.security_audit_event import SecurityAuditEvent


class PostgresSecurityAuditRepository:
    """Append-only security audit adapter with idempotent event identity."""

    def __init__(
        self,
        session_factory: Callable[[], Session] | sessionmaker | None = None,
        engine=None,
        session: Session | None = None,
    ):
        if session_factory is not None and not callable(session_factory):
            session = session_factory
            session_factory = None
        if session is not None and session_factory is None:

            def session_factory():
                return session

        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
            if getattr(engine.dialect, "name", None) == "sqlite":
                # SQLite unit tests have no Alembic bootstrap.
                SecurityAuditEvent.metadata.create_all(engine)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def append(self, record: SecurityAuditRecord) -> AppendResult:
        try:
            with self._session_factory() as session:
                with session.begin():
                    row = SecurityAuditEvent(
                        id=record.event_id,
                        request_id=record.request_id,
                        occurred_at=record.occurred_at,
                        event_type=record.event_type.value,
                        phase=record.phase.value,
                        outcome=record.outcome.value,
                        component_kind=record.component_kind,
                        component_name=record.component_name,
                        required_scope=record.required_scope,
                        tenant_id=record.tenant_id,
                        subject=record.subject,
                        reason_code=record.reason_code,
                        safe_details=dict(record.safe_details),
                    )
                    session.add(row)
                    session.flush()
                    return AppendResult(record.event_id, persisted=True, duplicate=False)
        except IntegrityError:
            with self._session_factory() as session:
                existing = session.execute(
                    select(SecurityAuditEvent).where(
                        SecurityAuditEvent.request_id == record.request_id,
                        SecurityAuditEvent.event_type == record.event_type.value,
                        SecurityAuditEvent.phase == record.phase.value,
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    return AppendResult(existing.id, persisted=True, duplicate=True)
            raise
