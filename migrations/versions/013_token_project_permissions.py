"""Add allowed_projects JSON column to tokens table."""

import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tokens",
        sa.Column(
            "allowed_projects",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[\"*\"]'"),
        ),
    )
    op.execute("UPDATE tokens SET allowed_projects = '[\"*\"]' WHERE allowed_projects IS NULL OR allowed_projects::text = '[]'")


def downgrade() -> None:
    op.drop_column("tokens", "allowed_projects")
