from importlib import import_module

from sqlalchemy import Index

from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.project import Project


def test_f003_migration_is_reversible_and_targets_only_documented_indexes():
    migration = import_module("migrations.versions.f003_entity_search_indexes")

    assert migration.revision == "f003_entity_search_indexes"
    assert migration.down_revision == "f001_foundation"
    assert {
        index.name
        for table in (Entity.__table__, Project.__table__)
        for index in table.indexes
        if isinstance(index, Index) and index.name.startswith("ix_entities_")
        and index.name.endswith("_search")
    } == {
        "ix_entities_tenant_key_active_search",
        "ix_entities_tenant_type_active_search",
        "ix_entities_tenant_name_prefix_search",
    }
    assert "ix_projects_tenant_active_snapshot" in {
        index.name for index in Project.__table__.indexes
    }
