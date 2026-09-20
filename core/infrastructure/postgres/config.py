from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class PostgresSettings(BaseSettings):
    database_url: SecretStr
    pool_size: int = 5
    max_overflow: int = 10
    pool_timeout: int = 30

    model_config = SettingsConfigDict(
        env_prefix="",
        case_sensitive=False,
        extra="ignore",
        hide_input_in_errors=True,
    )

    @model_validator(mode="after")
    def validate_settings(self):
        try:
            parsed = make_url(self.database_url.get_secret_value())
        except Exception as error:
            raise ValueError("DATABASE_URL must be a valid PostgreSQL psycopg2 URL") from error

        if parsed.drivername != "postgresql+psycopg2" or not parsed.host:
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg2 driver")
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            raise ValueError("DATABASE_URL port must be between 1 and 65535")
        if self.pool_size <= 0:
            raise ValueError("pool_size must be positive")
        if self.max_overflow <= 0:
            raise ValueError("max_overflow must be positive")
        if self.pool_timeout <= 0:
            raise ValueError("pool_timeout must be positive")
        return self

    @property
    def dialect(self) -> str:
        return "postgresql+psycopg2"
