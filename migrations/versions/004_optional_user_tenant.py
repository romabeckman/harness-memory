"""Allow users without an organization; identity creation no longer provisions one."""

import sqlalchemy as sa
from alembic import op

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "tenant_id", existing_type=sa.Uuid(), nullable=True)


def downgrade() -> None:
    op.execute("INSERT INTO tenants (id, key, name, status, metadata, created_at, updated_at) SELECT users.id, 'user-' || CAST(users.id AS TEXT), 'User ' || users.name || ' Tenant', 'active', '{}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP FROM users WHERE users.tenant_id IS NULL AND NOT EXISTS (SELECT 1 FROM tenants WHERE tenants.id = users.id)")
    op.execute("UPDATE users SET tenant_id = id WHERE tenant_id IS NULL")
    op.alter_column("users", "tenant_id", existing_type=sa.Uuid(), nullable=False)
