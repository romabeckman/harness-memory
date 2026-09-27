"""Create the final tables for fresh databases; indexes and relationships follow in 002."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def _json_object() -> sa.JSON:
    return sa.JSON().with_variant(JSONB(), "postgresql")


def _metadata_check(name: str, column: str = "metadata") -> sa.CheckConstraint:
    return sa.CheckConstraint(f"substr(CAST({column} AS TEXT), 1, 1) = '{{'", name=name)


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_tenants_key"),
        sa.CheckConstraint("length(trim(key)) > 0", name="ck_tenants_key_non_empty"),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_tenants_status_valid"),
        _metadata_check("ck_tenants_metadata_object"),
    )

    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("active_snapshot_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_projects_id_tenant"),
        sa.UniqueConstraint("key", name="uq_projects_key"),
        sa.UniqueConstraint("tenant_id", "key", name="uq_projects_tenant_key"),
        _metadata_check("ck_projects_metadata_object"),
    )

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("environment_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("publication_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("project_key", sa.String(255), nullable=False),
        sa.Column("project_name", sa.String(255), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_snapshots_id_tenant"),
        sa.UniqueConstraint("id", "project_id", "tenant_id", name="uq_snapshots_id_project_tenant"),
        _metadata_check("ck_snapshots_metadata_object"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "revision",
            name="uq_snapshots_tenant_project_environment_revision",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "payload_hash",
            name="uq_snapshots_tenant_project_environment_payload_hash",
        ),
    )

    op.create_table(
        "entities",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("entity_key", sa.String(length=255), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("identity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("canonical_key", sa.String(255), nullable=True),
        sa.Column("graph_position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "snapshot_id", "tenant_id", name="uq_entities_id_snapshot_tenant"
        ),
        sa.UniqueConstraint(
            "tenant_id", "snapshot_id", "entity_key", name="uq_entities_snapshot_key"
        ),
        _metadata_check("ck_entities_metadata_object"),
    )

    op.create_table(
        "relations",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("target_entity_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("provenance_kind", sa.String(length=32), nullable=False),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("source_identity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("target_identity_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("relation_ref", sa.String(255), nullable=False),
        sa.Column("graph_position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "snapshot_id", "tenant_id", name="uq_relations_id_snapshot_tenant"
        ),
        sa.CheckConstraint(
            "provenance_kind IN ('declared', 'inferred', 'observed', 'manual')",
            name="ck_relations_provenance_kind",
        ),
        _metadata_check("ck_relations_metadata_object"),
    )

    op.create_table(
        "evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("relation_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("source", sa.String(length=1024), nullable=False),
        sa.Column("excerpt", sa.String(length=4096), nullable=True),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("graph_position", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        _metadata_check("ck_evidence_metadata_object"),
    )

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
            "safe_details", sa.JSON().with_variant(postgresql.JSONB(), "postgresql"), nullable=False
        ),
        sa.CheckConstraint(
            "event_type IN ('publication', 'impact_analysis', 'authentication_failure', 'authorization_failure')",
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
            "event_type NOT IN ('authentication_failure', 'authorization_failure') OR (phase = 'completed' AND outcome = 'denied')",
            name="ck_security_audit_denial_state",
        ),
        sa.CheckConstraint(
            "event_type NOT IN ('publication', 'impact_analysis') OR (phase = 'attempted' AND outcome = 'pending') OR (phase = 'completed' AND outcome IN ('succeeded', 'failed'))",
            name="ck_security_audit_operation_state",
        ),
        sa.CheckConstraint(
            "event_type = 'authentication_failure' OR (tenant_id IS NOT NULL AND subject IS NOT NULL)",
            name="ck_security_audit_identity",
        ),
        sa.CheckConstraint(
            "length(trim(component_name)) > 0", name="ck_security_audit_component_name"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", "event_type", "phase", name="uq_security_audit_identity"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "tokens",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("user_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("service_account_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "scopes", sa.JSON(), nullable=False, server_default=sa.text("'[\"memory:read\"]'")
        ),
        sa.Column(
            "allowed_projects", sa.JSON(), nullable=False, server_default=sa.text("'[\"*\"]'")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
        sa.CheckConstraint(
            "(user_id IS NOT NULL AND service_account_id IS NULL) OR (user_id IS NULL AND service_account_id IS NOT NULL)",
            name="ck_token_owner_exactly_one",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR (expires_at > created_at AND expires_at <= created_at + INTERVAL '90 days')",
            name="ck_token_expiration_window",
        ),
    )

    op.create_table(
        "service_accounts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "environments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="other"),
        sa.Column("current_snapshot_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_environments_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "project_id", "name", name="uq_environments_tenant_project_name"
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_environments_name_non_empty"),
        _metadata_check("ck_environments_metadata_object"),
    )

    op.create_table(
        "knowledge_publications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("environment_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("deployment_id", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("snapshot_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_knowledge_publications_id_tenant"),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "environment_id",
            "deployment_id",
            name="uq_knowledge_publications_tenant_project_env_deploy",
        ),
        sa.CheckConstraint(
            "length(trim(deployment_id)) > 0",
            name="ck_knowledge_publications_deployment_id_non_empty",
        ),
        _metadata_check("ck_knowledge_publications_metadata_object"),
    )


def downgrade() -> None:
    op.drop_table("knowledge_publications")
    op.drop_table("environments")
    op.drop_table("service_accounts")
    op.drop_table("tokens")
    op.drop_table("users")
    op.drop_table("security_audit_events")
    op.drop_table("evidence")
    op.drop_table("relations")
    op.drop_table("entities")
    op.drop_table("snapshots")
    op.drop_table("projects")
    op.drop_table("tenants")
