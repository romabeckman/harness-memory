import os
import pytest
from sqlalchemy import text

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.schema_compatibility_checker import SchemaCompatibilityChecker

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


def test_startup_schema_compatibility_succeeds_when_fully_migrated():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))
    try:
        runtime.upgrade("head")
        checker = SchemaCompatibilityChecker()
        status = checker.check(runtime)
        assert status.is_compatible() is True
        assert status.current_revision == status.head_revision
    finally:
        runtime.dispose()


def test_detect_incompatibility_when_unapplied_migrations():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))
    try:
        runtime.upgrade("head")
        runtime.downgrade("base")
        checker = SchemaCompatibilityChecker()
        status = checker.check(runtime)
        assert status.is_compatible() is False
        assert status.current_revision != status.head_revision
    finally:
        runtime.upgrade("head")
        runtime.dispose()


def test_detect_incompatibility_when_alembic_version_missing():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))
    try:
        runtime.upgrade("head")
        with runtime.engine.begin() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version CASCADE"))
        checker = SchemaCompatibilityChecker()
        status = checker.check(runtime)
        assert status.is_compatible() is False
        assert status.current_revision is None
    finally:
        runtime.upgrade("head")
        runtime.dispose()
