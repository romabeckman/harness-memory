"""Seed a default admin user and project."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None

ADMIN_USER_ID = UUID("6e5c445f-77c8-4ed7-bc9c-3c9942ba2992")
DEFAULT_PROJECT_ID = UUID("4819f7b9-3c6b-4561-8d7c-1940b0a88712")
ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@harness-memory.local"
DEFAULT_PROJECT_KEY = "default"
DEFAULT_PROJECT_NAME = "Default Project"


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "INSERT INTO users (id, name, email, created_at) "
            "VALUES (:id, :name, :email, CURRENT_TIMESTAMP)"
        ).bindparams(sa.bindparam("id", type_=sa.Uuid(as_uuid=True))),
        {"id": ADMIN_USER_ID, "name": ADMIN_NAME, "email": ADMIN_EMAIL},
    )
    connection.execute(
        sa.text(
            "INSERT INTO projects (id, tenant_id, key, name) VALUES (:id, :tenant_id, :key, :name)"
        ).bindparams(sa.bindparam("id", type_=sa.Uuid(as_uuid=True))),
        {
            "id": DEFAULT_PROJECT_ID,
            "tenant_id": str(ADMIN_USER_ID),
            "key": DEFAULT_PROJECT_KEY,
            "name": DEFAULT_PROJECT_NAME,
        },
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        sa.text(
            "DELETE FROM projects "
            "WHERE id = :id AND tenant_id = :tenant_id AND key = :key AND name = :name "
            "AND NOT EXISTS ("
            "SELECT 1 FROM snapshots "
            "WHERE snapshots.project_id = projects.id "
            "AND snapshots.tenant_id = projects.tenant_id"
            ") "
            "AND NOT EXISTS ("
            "SELECT 1 FROM entities "
            "WHERE entities.project_id = projects.id "
            "AND entities.tenant_id = projects.tenant_id"
            ")"
        ).bindparams(sa.bindparam("id", type_=sa.Uuid(as_uuid=True))),
        {
            "id": DEFAULT_PROJECT_ID,
            "tenant_id": str(ADMIN_USER_ID),
            "key": DEFAULT_PROJECT_KEY,
            "name": DEFAULT_PROJECT_NAME,
        },
    )
    connection.execute(
        sa.text(
            "DELETE FROM users "
            "WHERE id = :id AND name = :name AND email = :email "
            "AND NOT EXISTS (SELECT 1 FROM tokens WHERE tokens.user_id = users.id)"
        ).bindparams(sa.bindparam("id", type_=sa.Uuid(as_uuid=True))),
        {"id": ADMIN_USER_ID, "name": ADMIN_NAME, "email": ADMIN_EMAIL},
    )
