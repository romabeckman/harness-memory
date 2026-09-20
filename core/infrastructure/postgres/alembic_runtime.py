from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from .config import PostgresSettings
from .engine_factory import PostgresEngineFactory
from .migrations_status import MigrationStatus


class AlembicRuntime:
    def __init__(self, settings: PostgresSettings):
        self.settings = settings
        self.engine = PostgresEngineFactory.create(settings)

    def upgrade(self, revision: str = "head") -> MigrationStatus:
        command.upgrade(self._config(), revision)
        return self.status()

    def downgrade(self, revision: str = "base") -> MigrationStatus:
        command.downgrade(self._config(), revision)
        return self.status()

    def status(self) -> MigrationStatus:
        config = self._config()
        head_revision = ScriptDirectory.from_config(config).get_current_head()
        with self.engine.connect() as connection:
            current_revision = self._current_revision(connection)
        return MigrationStatus(current_revision=current_revision, head_revision=head_revision)

    def dispose(self) -> None:
        self.engine.dispose()

    @staticmethod
    def _current_revision(connection: Connection) -> str | None:
        if not inspect(connection).has_table("alembic_version"):
            return None
        return MigrationContext.configure(connection).get_current_revision()

    def _config(self) -> Config:
        root = Path(__file__).resolve().parents[3]
        config = Config(str(root / "alembic.ini"))
        config.set_main_option("script_location", str(root / "migrations"))
        config.set_main_option(
            "sqlalchemy.url", self.settings.database_url.get_secret_value().replace("%", "%%")
        )
        return config
