import pytest
from pydantic import ValidationError

from core.infrastructure.postgres.config import PostgresSettings


def test_postgres_settings_accept_psycopg2_url():
    settings = PostgresSettings(
        database_url="postgresql+psycopg2://user:password@localhost:5432/database"
    )

    assert settings.database_url.get_secret_value().startswith("postgresql+psycopg2://")
    assert settings.dialect == "postgresql+psycopg2"


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///foundation.db",
        "postgresql+psycopg://user:password@localhost/database",
        "not-a-database-url",
    ],
)
def test_postgres_settings_reject_unsupported_url(database_url):
    with pytest.raises(ValidationError):
        PostgresSettings(database_url=database_url)


@pytest.mark.parametrize("field", ["pool_size", "max_overflow", "pool_timeout"])
def test_postgres_settings_reject_non_positive_pool_values(field):
    values = {
        "database_url": "postgresql+psycopg2://user:password@localhost/database",
        field: 0,
    }

    with pytest.raises(ValidationError) as error:
        PostgresSettings(**values)

    assert field in str(error.value)


def test_postgres_settings_redact_credentials_in_representation_and_errors():
    settings = PostgresSettings(
        database_url="postgresql+psycopg2://secret-user:secret-password@localhost/database"
    )

    assert "secret-user" not in repr(settings)
    assert "secret-password" not in repr(settings)

    with pytest.raises(ValidationError) as error:
        PostgresSettings(database_url="sqlite://secret-user:secret-password@localhost/database")

    assert "secret-user" not in str(error.value)
    assert "secret-password" not in str(error.value)
