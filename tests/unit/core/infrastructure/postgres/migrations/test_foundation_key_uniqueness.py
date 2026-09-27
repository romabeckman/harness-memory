from importlib import import_module
from unittest.mock import Mock
from uuid import uuid4

import pytest
import sqlalchemy as sa

from core.infrastructure.postgres.models.project import Project


@pytest.fixture
def foundation(monkeypatch):
    migration = import_module("migrations.versions.001_foundation")
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    metadata = sa.MetaData()
    for call in operations.create_table.call_args_list:
        name, *definitions = call.args
        if name in {"tenants", "projects"}:
            sa.Table(name, metadata, *definitions)
    engine = sa.create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    try:
        with engine.begin() as connection:
            yield connection, metadata.tables
    finally:
        engine.dispose()


def test_tenant_keys_are_globally_unique(foundation):
    connection, tables = foundation
    tenants = tables["tenants"]
    connection.execute(tenants.insert(), {"id": uuid4(), "key": "first", "name": "First"})
    connection.execute(tenants.insert(), {"id": uuid4(), "key": "second", "name": "Second"})

    with pytest.raises(sa.exc.IntegrityError):
        connection.execute(tenants.insert(), {"id": uuid4(), "key": "first", "name": "Duplicate"})


@pytest.mark.parametrize("same_tenant", [True, False])
def test_project_keys_are_globally_unique(foundation, same_tenant):
    connection, tables = foundation
    tenant_ids = [uuid4(), uuid4()]
    for index, tenant_id in enumerate(tenant_ids):
        connection.execute(
            tables["tenants"].insert(),
            {"id": tenant_id, "key": f"tenant-{index}", "name": "Tenant"},
        )
    projects = tables["projects"]
    connection.execute(
        projects.insert(), {"id": uuid4(), "tenant_id": tenant_ids[0], "key": "first"}
    )
    connection.execute(
        projects.insert(), {"id": uuid4(), "tenant_id": tenant_ids[1], "key": "second"}
    )

    with pytest.raises(sa.exc.IntegrityError):
        connection.execute(
            projects.insert(),
            {"id": uuid4(), "tenant_id": tenant_ids[0 if same_tenant else 1], "key": "first"},
        )


def test_project_model_matches_global_key_uniqueness():
    assert any(
        isinstance(constraint, sa.UniqueConstraint) and list(constraint.columns.keys()) == ["key"]
        for constraint in Project.__table__.constraints
    )
