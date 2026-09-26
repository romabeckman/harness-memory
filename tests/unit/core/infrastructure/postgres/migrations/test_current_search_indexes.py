from importlib import import_module
from unittest.mock import Mock


def test_current_search_migration_adds_reversible_global_and_metadata_indexes(monkeypatch):
    migration = import_module("migrations.versions.002_indexes_and_relationships")
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)

    migration.upgrade()

    statements = [call.args[0] for call in operations.execute.call_args_list]
    assert migration.down_revision == "001"
    assert any("CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql for sql in statements)
    assert any("gin_trgm_ops" in sql and "metadata" in sql for sql in statements)
    assert any("ix_entities_key_snapshot_occurrence" in sql for sql in statements)
    assert any("ix_projects_key_tenant_id" in sql for sql in statements)

    migration.downgrade()

    assert "ix_entities_metadata_trgm" in {
        call.args[0] for call in operations.drop_index.call_args_list
    }
