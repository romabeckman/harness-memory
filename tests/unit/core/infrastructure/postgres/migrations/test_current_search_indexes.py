from importlib import import_module
from types import SimpleNamespace


def test_current_search_migration_adds_reversible_global_and_metadata_indexes(monkeypatch):
    migration = import_module("migrations.versions.012_current_search_indexes")
    statements = []
    monkeypatch.setattr(migration.op, "get_bind", lambda: SimpleNamespace(
        dialect=SimpleNamespace(name="postgresql")))
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.down_revision == "011"
    assert "SET CONSTRAINTS ALL IMMEDIATE" in statements
    assert statements.index("SET CONSTRAINTS ALL IMMEDIATE") < next(
        index for index, sql in enumerate(statements) if "CREATE INDEX" in sql
    )
    assert any("CREATE EXTENSION IF NOT EXISTS pg_trgm" in sql for sql in statements)
    assert any("gin_trgm_ops" in sql and "metadata" in sql for sql in statements)
    assert any("ix_entities_key_snapshot_occurrence" in sql for sql in statements)
    assert any("ix_projects_key_tenant_id" in sql for sql in statements)
    statements.clear()

    migration.downgrade()

    assert any("DROP INDEX IF EXISTS ix_entities_metadata_trgm" in sql for sql in statements)
