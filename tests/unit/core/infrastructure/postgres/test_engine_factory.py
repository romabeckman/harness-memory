from unittest.mock import patch

from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory


def test_postgres_engine_factory_creates_without_connecting():
    settings = PostgresSettings(
        database_url="postgresql+psycopg2://user:password@localhost/database"
    )

    with patch("core.infrastructure.postgres.engine_factory.create_engine") as create:
        engine = PostgresEngineFactory.create(settings)

    create.assert_called_once()
    engine = create.return_value
    assert engine is not None
