from importlib import import_module
from uuid import UUID, uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def _legacy_database():
    engine = sa.create_engine("sqlite+pysqlite:///:memory:")
    metadata = sa.MetaData()
    # Legacy tables from 001-009 before 010 (no tenants table, tenant_id is string)
    sa.Table(
        "projects",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(255), nullable=False),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255)),
    )
    sa.Table(
        "users",
        metadata,
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    metadata.create_all(engine)
    return engine, engine.connect()


def _migration(connection, monkeypatch):
    migration = import_module("migrations.versions.010_tenant_foundation_forward")
    monkeypatch.setattr(
        migration,
        "op",
        Operations(MigrationContext.configure(connection)),
    )
    return migration


@pytest.fixture
def legacy_database():
    engine, connection = _legacy_database()
    try:
        yield connection
    finally:
        connection.close()
        engine.dispose()


def test_forward_migration_creates_tenants_and_backfills_distinct_identities(
    legacy_database, monkeypatch
):
    tenant_1 = str(uuid4())
    tenant_2 = str(uuid4())
    user_id = str(uuid4())

    legacy_database.execute(
        sa.text("INSERT INTO projects (id, tenant_id, key, name) VALUES (:id, :tenant_id, :key, :name)"),
        [
            {"id": str(uuid4()), "tenant_id": tenant_1, "key": "p1", "name": "P1"},
            {"id": str(uuid4()), "tenant_id": tenant_2, "key": "p2", "name": "P2"},
        ],
    )
    legacy_database.execute(
        sa.text("INSERT INTO users (id, name, email, created_at) VALUES (:id, :name, :email, CURRENT_TIMESTAMP)"),
        {"id": user_id, "name": "U1", "email": "u1@example.com"},
    )

    migration = _migration(legacy_database, monkeypatch)
    migration.upgrade()

    tenants = legacy_database.execute(sa.text("SELECT id, key, status FROM tenants")).fetchall()
    tenant_keys = {row[1] for row in tenants}

    assert tenant_1 in tenant_keys
    assert tenant_2 in tenant_keys
    assert user_id in tenant_keys

    # Check users has tenant_id column backfilled
    user_row = legacy_database.execute(sa.text("SELECT id, tenant_id FROM users")).one()
    assert UUID(user_row[0]) == UUID(user_row[1])


def test_forward_migration_fails_when_tenant_id_is_not_uuid(legacy_database, monkeypatch):
    legacy_database.execute(
        sa.text("INSERT INTO projects (id, tenant_id, key, name) VALUES (:id, :tenant_id, :key, :name)"),
        {"id": str(uuid4()), "tenant_id": "not-a-valid-uuid", "key": "p-bad", "name": "Bad Project"},
    )

    migration = _migration(legacy_database, monkeypatch)
    with pytest.raises(RuntimeError, match="Cannot convert non-UUID tenant_id 'not-a-valid-uuid'"):
        migration.upgrade()
