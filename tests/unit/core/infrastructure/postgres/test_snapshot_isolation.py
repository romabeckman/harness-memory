from unittest.mock import patch

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.create_postgres_engine import CreatePostgresEngine
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory


def test_engine_factory_uses_repeatable_read_for_snapshot_queries():
    settings = PostgresSettings(
        database_url="postgresql+psycopg2://user:password@localhost/database"
    )
    with patch("core.infrastructure.postgres.engine_factory.create_engine") as create:
        PostgresEngineFactory.create(settings)
    assert create.call_args.kwargs["isolation_level"] == "REPEATABLE READ"


def test_engine_creator_uses_repeatable_read_for_snapshot_queries():
    settings = PostgresSettings(
        database_url="postgresql+psycopg2://user:password@localhost/database"
    )
    with patch("core.infrastructure.postgres.create_postgres_engine.create_engine") as create:
        CreatePostgresEngine().execute(settings)
    assert create.call_args.kwargs["isolation_level"] == "REPEATABLE READ"
