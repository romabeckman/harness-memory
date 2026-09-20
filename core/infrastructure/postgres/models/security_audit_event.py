from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String, UniqueConstraint, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class SecurityAuditBase(DeclarativeBase):
    """Metadata isolated from foundation model assertions and migrations."""


class SecurityAuditEvent(SecurityAuditBase):
    __tablename__ = "security_audit_events"
    __table_args__ = (
        UniqueConstraint("request_id", "event_type", "phase", name="uq_security_audit_identity"),
        CheckConstraint(
            "length(trim(component_kind)) > 0", name="ck_security_audit_component_kind"
        ),
        CheckConstraint(
            "length(trim(component_name)) > 0", name="ck_security_audit_component_name"
        ),
        CheckConstraint(
            "event_type IN ('publication', 'impact_analysis', 'authentication_failure', "
            "'authorization_failure')",
            name="ck_security_audit_event_type",
        ),
        CheckConstraint("phase IN ('attempted', 'completed')", name="ck_security_audit_phase"),
        CheckConstraint(
            "outcome IN ('pending', 'denied', 'succeeded', 'failed')",
            name="ck_security_audit_outcome",
        ),
        CheckConstraint(
            "event_type NOT IN ('authentication_failure', 'authorization_failure') "
            "OR (phase = 'completed' AND outcome = 'denied')",
            name="ck_security_audit_denial_state",
        ),
        CheckConstraint(
            "event_type NOT IN ('publication', 'impact_analysis') "
            "OR (phase = 'attempted' AND outcome = 'pending') "
            "OR (phase = 'completed' AND outcome IN ('succeeded', 'failed'))",
            name="ck_security_audit_operation_state",
        ),
        CheckConstraint(
            "event_type = 'authentication_failure' OR "
            "(tenant_id IS NOT NULL AND subject IS NOT NULL)",
            name="ck_security_audit_identity",
        ),
        Index("ix_security_audit_tenant_time", "tenant_id", "occurred_at"),
        Index("ix_security_audit_event_time", "event_type", "occurred_at"),
        Index("ix_security_audit_request", "request_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    request_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    phase: Mapped[str] = mapped_column(String(32), nullable=False)
    outcome: Mapped[str] = mapped_column(String(32), nullable=False)
    component_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    component_name: Mapped[str] = mapped_column(String(255), nullable=False)
    required_scope: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    safe_details: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False, default=dict
    )
