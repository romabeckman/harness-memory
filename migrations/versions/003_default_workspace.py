"""Seed the default tenant, admin identity, project, and production environment."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None
ADMIN_USER_ID = UUID("6e5c445f-77c8-4ed7-bc9c-3c9942ba2992")
DEFAULT_TENANT_ID = UUID("6e5c445f-77c8-4ed7-bc9c-3c9942ba2992")
DEFAULT_PROJECT_ID = UUID("4819f7b9-3c6b-4561-8d7c-1940b0a88712")
DEFAULT_ENVIRONMENT_ID = UUID("7651edb7-844f-5d96-977b-10e691d41c53")
ADMIN_NAME = "Admin"
ADMIN_EMAIL = "admin@harness-memory.local"
DEFAULT_TENANT_KEY = "default"
DEFAULT_TENANT_NAME = "Default Tenant"
DEFAULT_PROJECT_KEY = "default"
DEFAULT_PROJECT_NAME = "Default Project"


def upgrade() -> None:
    op.execute(
        sa.text(
            "INSERT INTO tenants (id, key, name, status, metadata, created_at, "
            "updated_at) VALUES (:id, :key, :name, 'active', '{}', CURRENT_TIMESTAMP, "
            "CURRENT_TIMESTAMP)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_TENANT_ID),
            key=DEFAULT_TENANT_KEY,
            name=DEFAULT_TENANT_NAME,
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO users (id, tenant_id, name, email, created_at) VALUES (:id, "
            ":tenant_id, :name, :email, CURRENT_TIMESTAMP)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=ADMIN_USER_ID),
            sa.bindparam("tenant_id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_TENANT_ID),
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
        )
    )
    op.execute(
        sa.text(
            "INSERT INTO projects (id, tenant_id, key, name) VALUES (:id, :tenant_id, :key, :name)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_PROJECT_ID),
            sa.bindparam("tenant_id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_TENANT_ID),
            key=DEFAULT_PROJECT_KEY,
            name=DEFAULT_PROJECT_NAME,
        )
    )

    op.execute(
        sa.text(
            "INSERT INTO environments "
            "(id, tenant_id, project_id, name, type, metadata, created_at, updated_at) "
            "VALUES (:id, :tenant_id, :project_id, 'production', 'production', '{}', "
            "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
        ).bindparams(
            sa.bindparam("id", value=DEFAULT_ENVIRONMENT_ID, type_=sa.Uuid(as_uuid=True)),
            sa.bindparam("tenant_id", value=DEFAULT_TENANT_ID, type_=sa.Uuid(as_uuid=True)),
            sa.bindparam("project_id", value=DEFAULT_PROJECT_ID, type_=sa.Uuid(as_uuid=True)),
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM environments WHERE id = :id AND tenant_id = :tenant_id "
            "AND project_id = :project_id AND name = 'production' AND type = 'production' "
            "AND current_snapshot_id IS NULL AND CAST(metadata AS TEXT) = '{}' "
            "AND NOT EXISTS (SELECT 1 FROM snapshots WHERE snapshots.environment_id = "
            "environments.id) "
            "AND NOT EXISTS (SELECT 1 FROM knowledge_publications "
            "WHERE knowledge_publications.environment_id = environments.id)"
        ).bindparams(
            sa.bindparam("id", value=DEFAULT_ENVIRONMENT_ID, type_=sa.Uuid(as_uuid=True)),
            sa.bindparam("tenant_id", value=DEFAULT_TENANT_ID, type_=sa.Uuid(as_uuid=True)),
            sa.bindparam("project_id", value=DEFAULT_PROJECT_ID, type_=sa.Uuid(as_uuid=True)),
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM projects WHERE id = :id AND tenant_id = :tenant_id AND key = "
            ":key AND name = :name AND NOT EXISTS (SELECT 1 FROM environments WHERE "
            "environments.project_id = projects.id) AND NOT EXISTS (SELECT 1 FROM "
            "knowledge_publications WHERE knowledge_publications.project_id = "
            "projects.id) AND NOT EXISTS (SELECT 1 FROM snapshots WHERE "
            "snapshots.project_id = projects.id AND snapshots.tenant_id = "
            "projects.tenant_id) AND NOT EXISTS (SELECT 1 FROM entities WHERE "
            "entities.project_id = projects.id AND entities.tenant_id = "
            "projects.tenant_id)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_PROJECT_ID),
            sa.bindparam("tenant_id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_TENANT_ID),
            key=DEFAULT_PROJECT_KEY,
            name=DEFAULT_PROJECT_NAME,
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM users WHERE id = :id AND name = :name AND email = :email AND "
            "NOT EXISTS (SELECT 1 FROM tokens WHERE tokens.user_id = users.id)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=ADMIN_USER_ID),
            name=ADMIN_NAME,
            email=ADMIN_EMAIL,
        )
    )
    op.execute(
        sa.text(
            "DELETE FROM tenants WHERE id = :id AND key = :key AND name = :name AND "
            "NOT EXISTS (SELECT 1 FROM projects WHERE projects.tenant_id = tenants.id)"
            " AND NOT EXISTS (SELECT 1 FROM users WHERE users.tenant_id = tenants.id) "
            "AND NOT EXISTS (SELECT 1 FROM service_accounts WHERE "
            "service_accounts.tenant_id = tenants.id)"
        ).bindparams(
            sa.bindparam("id", type_=sa.Uuid(as_uuid=True), value=DEFAULT_TENANT_ID),
            key=DEFAULT_TENANT_KEY,
            name=DEFAULT_TENANT_NAME,
        )
    )
