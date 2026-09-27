import os

import pytest
from sqlalchemy import inspect

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.migrations import AlembicRuntime

DATABASE_URL = os.getenv("TEST_DATABASE_URL")


pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


def test_initial_migration_creates_all_final_tables():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))

    runtime.upgrade("head")
    with runtime.engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())

    assert {
        "projects",
        "snapshots",
        "entities",
        "relations",
        "evidence",
        "tenants",
        "users",
        "tokens",
        "service_accounts",
        "security_audit_events",
        "environments",
        "knowledge_publications",
        "alembic_version",
    } <= tables


def test_initial_migration_is_idempotent_and_status_is_read_only():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))

    runtime.upgrade("head")
    before = runtime.status()
    runtime.upgrade("head")
    after = runtime.status()

    assert before == after
    assert after.is_current
    assert after.head_revision == "004"


def test_initial_migration_downgrades_to_base():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))

    runtime.upgrade("head")
    runtime.downgrade("base")
    with runtime.engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())

    assert tables <= {"alembic_version"}
