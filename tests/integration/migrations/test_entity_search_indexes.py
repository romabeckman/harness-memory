import os

import pytest
from sqlalchemy import inspect

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.migrations import AlembicRuntime

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


def test_f003_upgrade_creates_four_search_indexes_without_replacing_foundation_indexes():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))
    runtime.upgrade("head")

    with runtime.engine.connect() as connection:
        indexes = {
            index["name"]
            for table in ("projects", "entities")
            for index in inspect(connection).get_indexes(table)
        }

    assert {
        "ix_entities_tenant_key_active_search",
        "ix_entities_tenant_type_active_search",
        "ix_entities_tenant_name_prefix_search",
        "ix_entities_snapshot_key",
        "ix_projects_tenant_key",
    } <= indexes
