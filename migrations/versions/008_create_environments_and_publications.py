"""Add environments, publications, and environment snapshot pointers."""

from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "008"
down_revision = "007"
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
        "environments",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
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
        sa.CheckConstraint("length(trim(tenant_id)) > 0", name="ck_environments_tenant_id_non_empty"),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_environments_name_non_empty"),
        _metadata_check("ck_environments_metadata_object"),
        sa.ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            name="fk_environments_project_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["current_snapshot_id", "tenant_id"],
            ["snapshots.id", "snapshots.tenant_id"],
            name="fk_environments_current_snapshot",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_environments_tenant_project_name", "environments", ["tenant_id", "project_id", "name"]
    )

    op.add_column("snapshots", sa.Column("environment_id", sa.Uuid(as_uuid=True), nullable=True))
    op.add_column("snapshots", sa.Column("publication_id", sa.Uuid(as_uuid=True), nullable=True))

    op.create_table(
        "knowledge_publications",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("tenant_id", sa.String(length=255), nullable=False),
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
            "length(trim(tenant_id)) > 0", name="ck_knowledge_publications_tenant_id_non_empty"
        ),
        sa.CheckConstraint(
            "length(trim(deployment_id)) > 0",
            name="ck_knowledge_publications_deployment_id_non_empty",
        ),
        _metadata_check("ck_knowledge_publications_metadata_object"),
        sa.ForeignKeyConstraint(
            ["project_id", "tenant_id"],
            ["projects.id", "projects.tenant_id"],
            name="fk_knowledge_publications_project_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["environment_id", "tenant_id"],
            ["environments.id", "environments.tenant_id"],
            name="fk_knowledge_publications_environment_tenant",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["snapshot_id", "tenant_id"],
            ["snapshots.id", "snapshots.tenant_id"],
            name="fk_knowledge_publications_snapshot_tenant",
            ondelete="SET NULL",
        ),
    )
    op.create_index(
        "ix_knowledge_publications_lookup",
        "knowledge_publications",
        ["tenant_id", "project_id", "environment_id", "deployment_id"],
    )

    # Backfill: seed production environment for existing projects
    connection = op.get_bind()
    projects = connection.execute(
        sa.text("SELECT id, tenant_id, active_snapshot_id FROM projects")
    ).fetchall()
    for proj in projects:
        env_id = uuid4()
        connection.execute(
            sa.text(
                "INSERT INTO environments (id, tenant_id, project_id, name, type, current_snapshot_id, metadata, created_at, updated_at) "
                "VALUES (:id, :tenant_id, :project_id, 'production', 'production', :snapshot_id, '{}', NOW(), NOW())"
            ),
            {
                "id": env_id,
                "tenant_id": proj.tenant_id,
                "project_id": proj.id,
                "snapshot_id": proj.active_snapshot_id,
            },
        )
        if proj.active_snapshot_id:
            connection.execute(
                sa.text(
                    "UPDATE snapshots SET environment_id = :env_id WHERE id = :snapshot_id AND tenant_id = :tenant_id"
                ),
                {
                    "env_id": env_id,
                    "snapshot_id": proj.active_snapshot_id,
                    "tenant_id": proj.tenant_id,
                },
            )


def downgrade() -> None:
    op.drop_table("knowledge_publications")
    op.drop_column("snapshots", "publication_id")
    op.drop_column("snapshots", "environment_id")
    op.drop_table("environments")
