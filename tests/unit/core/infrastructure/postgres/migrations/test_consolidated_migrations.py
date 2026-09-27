from importlib import import_module
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory

TABLES = {
    "tenants",
    "projects",
    "snapshots",
    "entities",
    "relations",
    "evidence",
    "security_audit_events",
    "users",
    "tokens",
    "service_accounts",
    "environments",
    "knowledge_publications",
}


def test_history_contains_ordered_revisions():
    scripts = ScriptDirectory.from_config(Config("alembic.ini"))
    assert [(item.revision, item.down_revision) for item in scripts.walk_revisions()] == [
        ("005", "004"),
        ("004", "003"),
        ("003", "002"),
        ("002", "001"),
        ("001", None),
    ]


def test_foundation_creates_final_tables_without_indexes_relationships_or_data(monkeypatch):
    migration = import_module("migrations.versions.001_foundation")
    operations = Mock()
    monkeypatch.setattr(migration, "op", operations)
    migration.upgrade()
    assert {call.args[0] for call in operations.create_table.call_args_list} == TABLES
    assert {call[0] for call in operations.method_calls} == {"create_table"}
    tables = {
        call.args[0]: sa.Table(*call.args[:1], sa.MetaData(), *call.args[1:])
        for call in operations.create_table.call_args_list
    }
    assert all(not table.foreign_keys and not table.indexes for table in tables.values())
    assert "payload" not in tables["snapshots"].c
    for table, columns in {
        "snapshots": {"project_key", "generated_at"},
        "entities": {"graph_position"},
        "relations": {"relation_ref", "graph_position"},
        "evidence": {"graph_position"},
        "tokens": {"scopes", "allowed_projects"},
    }.items():
        for column in columns:
            assert tables[table].c[column].nullable is False
    assert tables["tokens"].c.user_id.nullable
    assert tables["tokens"].c.service_account_id.nullable
    assert tables["tokens"].c.expires_at.nullable
    assert tables["service_accounts"].c.tenant_id.nullable
    assert not tables["users"].c.tenant_id.nullable
    assert not tables["projects"].c.tenant_id.nullable
    operations.reset_mock()
    migration.downgrade()
    assert {call.args[0] for call in operations.drop_table.call_args_list} == TABLES
    assert {call[0] for call in operations.method_calls} == {"drop_table"}


def test_relationships_and_indexes_are_reversible_postgresql_ddl(monkeypatch):
    migration = import_module("migrations.versions.002_indexes_and_relationships")
    output = StringIO()
    context = MigrationContext.configure(
        dialect_name="postgresql", opts={"as_sql": True, "output_buffer": output}
    )
    monkeypatch.setattr(migration, "op", Operations(context))
    migration.upgrade()
    sql = output.getvalue()
    assert "CREATE TABLE" not in sql
    assert "INSERT INTO" not in sql
    assert "FOREIGN KEY" in sql
    assert "DEFERRABLE INITIALLY DEFERRED" in sql
    assert "ON DELETE RESTRICT" in sql
    assert "gin_trgm_ops" in sql
    assert "ix_projects_key_tenant_id" in sql
    assert "ix_entities_tenant_name_prefix_search" in sql
    output.truncate(0)
    output.seek(0)
    migration.downgrade()
    assert "DROP INDEX" in output.getvalue()
    assert "DROP CONSTRAINT" in output.getvalue()
    assert "DROP TABLE" not in output.getvalue()


def test_revisions_do_not_import_mutable_application_models():
    for path in Path("migrations/versions").glob("[0-9]*.py"):
        assert "core.infrastructure.postgres.models" not in path.read_text(encoding="utf-8")


def test_full_chain_renders_upgrade_and_downgrade_without_a_database(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    output = StringIO()
    config = Config("alembic.ini", output_buffer=output)
    config.set_main_option("sqlalchemy.url", "postgresql://unused:unused@localhost/unused")

    command.upgrade(config, "head", sql=True)

    sql = output.getvalue()
    assert sql.count("CREATE TABLE ") == len(TABLES) + 2  # Alembic version table and project_links.
    assert sql.count(" FOREIGN KEY(") == 28
    assert sql.count("CREATE INDEX ") == 36
    assert sql.count("INSERT INTO tenants ") == 1
    assert sql.count("INSERT INTO users ") == 1
    assert sql.count("INSERT INTO projects ") == 1
    assert sql.count("INSERT INTO environments ") == 1
    assert "admin@harness-memory.local" in sql
    assert "'production'" in sql
    assert sql.index("CREATE TABLE knowledge_publications") < sql.index("ADD CONSTRAINT")
    assert sql.index("CREATE INDEX") < sql.index("INSERT INTO tenants")
    output.truncate(0)
    output.seek(0)

    command.downgrade(config, "003:base", sql=True)

    sql = output.getvalue()
    assert sql.count("DROP TABLE ") == len(TABLES)
    assert "DELETE FROM alembic_version" in sql
    assert sql.count("DROP INDEX ") == 34
    assert sql.count("DROP CONSTRAINT ") == 25
    assert sql.index("DELETE FROM tenants") < sql.index("DROP INDEX")
    assert sql.index("DROP CONSTRAINT") < sql.index("DROP TABLE")
