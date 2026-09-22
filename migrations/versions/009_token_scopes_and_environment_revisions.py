"""Persist exact token scopes and scope snapshot revisions by environment."""

import sqlalchemy as sa
from alembic import op

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tokens",
        sa.Column(
            "scopes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"memory:read\"]'"),
        ),
    )
    op.drop_constraint("uq_snapshots_tenant_project_revision", "snapshots", type_="unique")
    op.drop_constraint("uq_snapshots_tenant_project_payload_hash", "snapshots", type_="unique")
    op.create_unique_constraint(
        "uq_snapshots_tenant_project_environment_revision",
        "snapshots",
        ["tenant_id", "project_id", "environment_id", "revision"],
    )
    op.create_unique_constraint(
        "uq_snapshots_tenant_project_environment_payload_hash",
        "snapshots",
        ["tenant_id", "project_id", "environment_id", "payload_hash"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_snapshots_tenant_project_environment_payload_hash", "snapshots", type_="unique"
    )
    op.drop_constraint(
        "uq_snapshots_tenant_project_environment_revision", "snapshots", type_="unique"
    )
    op.create_unique_constraint(
        "uq_snapshots_tenant_project_revision",
        "snapshots",
        ["tenant_id", "project_id", "revision"],
    )
    op.create_unique_constraint(
        "uq_snapshots_tenant_project_payload_hash",
        "snapshots",
        ["tenant_id", "project_id", "payload_hash"],
    )
    op.drop_column("tokens", "scopes")
