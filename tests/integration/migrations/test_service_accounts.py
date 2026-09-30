import os

import pytest
from sqlalchemy import inspect

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.migrations import AlembicRuntime

DATABASE_URL = os.getenv("TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not DATABASE_URL, reason="TEST_DATABASE_URL is required for PostgreSQL integration tests"
)


def test_migration_adds_service_accounts_and_optional_token_expiration():
    runtime = AlembicRuntime(PostgresSettings(database_url=DATABASE_URL))

    try:
        runtime.upgrade("head")
        inspector = inspect(runtime.engine)
        token_columns = {column["name"]: column for column in inspector.get_columns("tokens")}

        assert "service_accounts" in inspector.get_table_names()
        account_columns = {
            column["name"]: column for column in inspector.get_columns("service_accounts")
        }
        assert account_columns["tenant_id"]["nullable"] is True
        assert token_columns["user_id"]["nullable"] is True
        assert token_columns["service_account_id"]["nullable"] is True
        assert token_columns["expires_at"]["nullable"] is True
        assert "ck_token_owner_exactly_one" in {
            item["name"] for item in inspector.get_check_constraints("tokens")
        }
        assert "ck_token_expiration_window" not in {
            item["name"] for item in inspector.get_check_constraints("tokens")
        }
    finally:
        runtime.engine.dispose()
