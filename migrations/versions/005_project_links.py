"""Create project_links table with canonical uniqueness, check constraint, cascading foreign keys, and indexes."""

import sqlalchemy as sa
from alembic import op

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_links",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_a_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("project_b_id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["project_a_id"],
            ["projects.id"],
            name="fk_project_links_project_a_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_b_id"],
            ["projects.id"],
            name="fk_project_links_project_b_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
            name="fk_project_links_created_by",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("project_a_id", "project_b_id", name="uq_project_links_a_b"),
        sa.CheckConstraint(
            "project_a_id <> project_b_id",
            name="ck_project_links_distinct_projects",
        ),
    )
    op.create_index(
        "ix_project_links_project_a_id",
        "project_links",
        ["project_a_id"],
    )
    op.create_index(
        "ix_project_links_project_b_id",
        "project_links",
        ["project_b_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_project_links_project_b_id", table_name="project_links")
    op.drop_index("ix_project_links_project_a_id", table_name="project_links")
    op.drop_table("project_links")
