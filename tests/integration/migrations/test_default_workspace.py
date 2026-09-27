import importlib
import os

import pytest
from sqlalchemy import select

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.migrations import AlembicRuntime
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.project import Project

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


def test_migration_head_creates_default_admin_tenant_and_project():
    migration = importlib.import_module("migrations.versions.003_default_workspace")
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))

    try:
        runtime.upgrade("head")
        with runtime.engine.connect() as connection:
            admin = (
                connection.execute(
                    select(ApiUser.id, ApiUser.name, ApiUser.email).where(
                        ApiUser.id == migration.ADMIN_USER_ID
                    )
                )
                .mappings()
                .one()
            )
            project = (
                connection.execute(
                    select(Project.id, Project.tenant_id, Project.key, Project.name).where(
                        Project.id == migration.DEFAULT_PROJECT_ID
                    )
                )
                .mappings()
                .one()
            )

        assert admin["name"] == migration.ADMIN_NAME
        assert admin["email"] == migration.ADMIN_EMAIL
        assert project["tenant_id"] == str(admin["id"])
        assert project["key"] == migration.DEFAULT_PROJECT_KEY
        assert project["name"] == migration.DEFAULT_PROJECT_NAME
    finally:
        runtime.engine.dispose()
