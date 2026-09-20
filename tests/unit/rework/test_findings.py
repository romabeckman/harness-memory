from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import CheckConstraint, create_engine, insert
from sqlalchemy.exc import SQLAlchemyError, StatementError

from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.project import Project
from harness_memory_mcp.migration_cli import MigrationCLI

REVISION_PATH = Path(__file__).parents[3] / "migrations" / "versions" / "001_foundation.py"


def test_initial_revision_declares_only_its_owned_schema():
    source = REVISION_PATH.read_text(encoding="utf-8")

    assert "Base.metadata.create_all" not in source
    assert "Base.metadata.drop_all" not in source
    assert "op.create_table" in source


def test_migration_status_propagates_schema_inspection_failures():
    with patch(
        "core.infrastructure.postgres.alembic_runtime.inspect",
        side_effect=SQLAlchemyError("catalog permission denied"),
    ):
        with pytest.raises(SQLAlchemyError, match="catalog permission denied"):
            AlembicRuntime._current_revision(object())


def test_migration_cli_redacts_username_from_authentication_errors():
    message = "password authentication failed for user secret-user"

    redacted = MigrationCLI._redact(message)

    assert "secret-user" not in redacted
    assert "authentication failed" in redacted


@pytest.mark.parametrize("port", [0, 65536])
def test_postgres_settings_reject_invalid_database_port(port):
    with pytest.raises(ValueError):
        PostgresSettings(
            database_url=f"postgresql+psycopg2://user:password@localhost:{port}/database"
        )


def test_project_schema_rejects_empty_tenant_id():
    checks = [
        constraint
        for constraint in Project.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    ]

    assert any("tenant_id" in str(check.sqltext) for check in checks)


def test_project_persistence_rejects_array_metadata():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)

    with engine.begin() as connection:
        with pytest.raises((StatementError, ValueError)):
            connection.execute(
                insert(Project).values(
                    id=uuid4(),
                    tenant_id="tenant-a",
                    key="project-a",
                    metadata_json=[],
                )
            )
