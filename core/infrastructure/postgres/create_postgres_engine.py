from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from .config import PostgresSettings


class CreatePostgresEngine:
    def execute(self, settings: PostgresSettings) -> Engine:
        return create_engine(
            settings.database_url.get_secret_value(),
            pool_pre_ping=True,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.pool_timeout,
            isolation_level="REPEATABLE READ",
        )
