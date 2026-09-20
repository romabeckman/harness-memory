"""Create append-only security audit events."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "f008_security_audit_events"
down_revision = "f006_canonical_impact_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("request_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("phase", sa.String(length=32), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("component_kind", sa.String(length=64), nullable=False),
        sa.Column("component_name", sa.String(length=255), nullable=False),
        sa.Column("required_scope", sa.String(length=64), nullable=True),
        sa.Column("tenant_id", sa.String(length=255), nullable=True),
        sa.Column("subject", sa.String(length=255), nullable=True),
        sa.Column("reason_code", sa.String(length=128), nullable=True),
        sa.Column(
            "safe_details",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "event_type IN ('publication', 'impact_analysis', 'authentication_failure', "
            "'authorization_failure')",
            name="ck_security_audit_event_type",
        ),
        sa.CheckConstraint("phase IN ('attempted', 'completed')", name="ck_security_audit_phase"),
        sa.CheckConstraint(
            "outcome IN ('pending', 'denied', 'succeeded', 'failed')",
            name="ck_security_audit_outcome",
        ),
        sa.CheckConstraint(
            "length(trim(component_kind)) > 0", name="ck_security_audit_component_kind"
        ),
        sa.CheckConstraint(
            "event_type NOT IN ('authentication_failure', 'authorization_failure') "
            "OR (phase = 'completed' AND outcome = 'denied')",
            name="ck_security_audit_denial_state",
        ),
        sa.CheckConstraint(
            "event_type NOT IN ('publication', 'impact_analysis') "
            "OR (phase = 'attempted' AND outcome = 'pending') "
            "OR (phase = 'completed' AND outcome IN ('succeeded', 'failed'))",
            name="ck_security_audit_operation_state",
        ),
        sa.CheckConstraint(
            "event_type = 'authentication_failure' OR "
            "(tenant_id IS NOT NULL AND subject IS NOT NULL)",
            name="ck_security_audit_identity",
        ),
        sa.CheckConstraint(
            "length(trim(component_name)) > 0", name="ck_security_audit_component_name"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "event_type", "phase", name="uq_security_audit_identity"),
    )
    op.create_index(
        "ix_security_audit_tenant_time", "security_audit_events", ["tenant_id", "occurred_at"]
    )
    op.create_index(
        "ix_security_audit_event_time", "security_audit_events", ["event_type", "occurred_at"]
    )
    op.create_index("ix_security_audit_request", "security_audit_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_security_audit_request", table_name="security_audit_events")
    op.drop_index("ix_security_audit_event_time", table_name="security_audit_events")
    op.drop_index("ix_security_audit_tenant_time", table_name="security_audit_events")
    op.drop_table("security_audit_events")
