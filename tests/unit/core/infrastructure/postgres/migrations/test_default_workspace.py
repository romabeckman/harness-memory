from importlib import import_module
from uuid import UUID

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _database():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    sa.Table(
        "tenants",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("key", sa.String(255), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("metadata", sa.String(1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    sa.Table(
        "tokens",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
    )
    sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
        sa.UniqueConstraint("tenant_id", "key"),
    )
    sa.Table(
        "snapshots",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
    )
    sa.Table(
        "entities",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(255), nullable=False),
    )
    metadata.create_all(engine)
    return engine, engine.connect()


def _migration(connection, monkeypatch):
    migration = import_module("migrations.versions.006_default_workspace")
    monkeypatch.setattr(
        migration,
        "op",
        Operations(MigrationContext.configure(connection)),
    )
    return migration


@pytest.fixture
def database():
    engine, connection = _database()
    try:
        yield connection
    finally:
        connection.close()
        engine.dispose()


def test_upgrade_seeds_admin_user_default_tenant_and_project(database, monkeypatch):
    migration = _migration(database, monkeypatch)

    migration.upgrade()

    admin = database.execute(sa.text("SELECT id, name, email FROM users")).one()
    project = database.execute(sa.text("SELECT id, tenant_id, key, name FROM projects")).one()
    assert database.scalar(sa.text("SELECT count(*) FROM tenants")) == 1
    assert admin.name == "Admin"
    assert admin.email == "admin@harness-memory.local"
    assert UUID(project.tenant_id) == UUID(admin.id)
    assert project.key == "default"
    assert project.name == "Default Project"


def test_downgrade_removes_only_unused_seed_rows(database, monkeypatch):
    migration = _migration(database, monkeypatch)
    migration.upgrade()

    migration.downgrade()

    assert database.scalar(sa.text("SELECT count(*) FROM tenants")) == 0
    assert database.scalar(sa.text("SELECT count(*) FROM users")) == 0
    assert database.scalar(sa.text("SELECT count(*) FROM projects")) == 0


def test_downgrade_preserves_seed_rows_with_user_data(database, monkeypatch):
    migration = _migration(database, monkeypatch)
    migration.upgrade()
    admin_id, project_id, tenant_id = database.execute(
        sa.text("SELECT users.id, projects.id, projects.tenant_id FROM users CROSS JOIN projects")
    ).one()
    database.execute(
        sa.text("INSERT INTO tokens (id, user_id) VALUES (:id, :user_id)"),
        {"id": "token-1", "user_id": admin_id},
    )
    database.execute(
        sa.text(
            "INSERT INTO snapshots (id, project_id, tenant_id) "
            "VALUES (:id, :project_id, :tenant_id)"
        ),
        {"id": "snapshot-1", "project_id": project_id, "tenant_id": tenant_id},
    )

    migration.downgrade()

    assert database.scalar(sa.text("SELECT count(*) FROM users")) == 1
    assert database.scalar(sa.text("SELECT count(*) FROM projects")) == 1
