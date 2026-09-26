"""Create and remove the foundation tables."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def _json_object() -> sa.JSON:
    return sa.JSON().with_variant(JSONB(), "postgresql")


def _metadata_check(name: str, column: str = "metadata") -> sa.CheckConstraint:
    return sa.CheckConstraint(
        f"substr(CAST({column} AS TEXT), 1, 1) = '{{'",
        name=name,
    )


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
    op.create_index("ix_tenants_key", "tenants", ["key"])

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
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_projects_tenant_id", ondelete="RESTRICT"
        ),
        _metadata_check("ck_projects_metadata_object"),
    )
    op.create_index("ix_projects_tenant_key", "projects", ["tenant_id", "key"])

    op.create_table(
        "snapshots",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("schema_version", sa.String(length=64), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("payload", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column("metadata", _json_object(), server_default=sa.text("'{}'"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", "tenant_id", name="uq_snapshots_id_tenant"),
        sa.UniqueConstraint("id", "project_id", "tenant_id", name="uq_snapshots_id_project_tenant"),
        sa.UniqueConstraint(
            "tenant_id", "project_id", "revision", name="uq_snapshots_tenant_project_revision"
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "project_id",
            "payload_hash",
            name="uq_snapshots_tenant_project_payload_hash",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_snapshots_tenant_id", ondelete="RESTRICT"
        ),
        _metadata_check("ck_snapshots_metadata_object"),
        _metadata_check("ck_snapshots_payload_object", "payload"),
    )
    op.create_index(
        "ix_snapshots_tenant_project_revision",
        "snapshots",
        ["tenant_id", "project_id", "revision"],
    )
    op.create_index(
        "ix_snapshots_tenant_project_hash",
        "snapshots",
        ["tenant_id", "project_id", "payload_hash"],
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "snapshot_id", "tenant_id", name="uq_entities_id_snapshot_tenant"
        ),
        sa.UniqueConstraint(
            "tenant_id", "snapshot_id", "entity_key", name="uq_entities_snapshot_key"
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_entities_tenant_id", ondelete="RESTRICT"
        ),
        _metadata_check("ck_entities_metadata_object"),
    )
    op.create_index(
        "ix_entities_snapshot_key", "entities", ["tenant_id", "snapshot_id", "entity_key"]
    )
    op.create_index("ix_entities_project", "entities", ["tenant_id", "project_id"])

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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "id", "snapshot_id", "tenant_id", name="uq_relations_id_snapshot_tenant"
        ),
        sa.CheckConstraint(
            "provenance_kind IN ('declared', 'inferred', 'observed', 'manual')",
            name="ck_relations_provenance_kind",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_relations_tenant_id", ondelete="RESTRICT"
        ),
        _metadata_check("ck_relations_metadata_object"),
    )
    op.create_index("ix_relations_snapshot", "relations", ["tenant_id", "snapshot_id"])
    op.create_index(
        "ix_relations_source", "relations", ["tenant_id", "snapshot_id", "source_entity_id"]
    )
    op.create_index(
        "ix_relations_target", "relations", ["tenant_id", "snapshot_id", "target_entity_id"]
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], name="fk_evidence_tenant_id", ondelete="RESTRICT"
        ),
        _metadata_check("ck_evidence_metadata_object"),
    )
    op.create_index("ix_evidence_snapshot", "evidence", ["tenant_id", "snapshot_id"])
    op.create_index(
        "ix_evidence_relation", "evidence", ["tenant_id", "snapshot_id", "relation_id"]
    )

    op.create_foreign_key(
        "fk_snapshots_project_tenant",
        "snapshots",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_entities_project_tenant",
        "entities",
        "projects",
        ["project_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_entities_snapshot_project_tenant",
        "entities",
        "snapshots",
        ["snapshot_id", "project_id", "tenant_id"],
        ["id", "project_id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_relations_snapshot_tenant",
        "relations",
        "snapshots",
        ["snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_relations_source_entity_scope",
        "relations",
        "entities",
        ["source_entity_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_relations_target_entity_scope",
        "relations",
        "entities",
        ["target_entity_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evidence_snapshot_tenant",
        "evidence",
        "snapshots",
        ["snapshot_id", "tenant_id"],
        ["id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_evidence_relation_scope",
        "evidence",
        "relations",
        ["relation_id", "snapshot_id", "tenant_id"],
        ["id", "snapshot_id", "tenant_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_projects_active_snapshot",
        "projects",
        "snapshots",
        ["active_snapshot_id", "id", "tenant_id"],
        ["id", "project_id", "tenant_id"],
        ondelete="SET NULL",
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_index("ix_evidence_relation", table_name="evidence")
    op.drop_index("ix_evidence_snapshot", table_name="evidence")
    op.drop_table("evidence")
    op.drop_index("ix_relations_target", table_name="relations")
    op.drop_index("ix_relations_source", table_name="relations")
    op.drop_index("ix_relations_snapshot", table_name="relations")
    op.drop_table("relations")
    op.drop_index("ix_entities_project", table_name="entities")
    op.drop_index("ix_entities_snapshot_key", table_name="entities")
    op.drop_table("entities")
    op.drop_constraint("fk_projects_active_snapshot", "projects", type_="foreignkey")
    op.drop_index("ix_snapshots_tenant_project_hash", table_name="snapshots")
    op.drop_index("ix_snapshots_tenant_project_revision", table_name="snapshots")
    op.drop_table("snapshots")
    op.drop_index("ix_projects_tenant_key", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_tenants_key", table_name="tenants")
    op.drop_table("tenants")
