import sys
from collections.abc import Sequence

from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.inspect_migration_status import InspectMigrationStatus
from core.infrastructure.postgres.upgrade_database import UpgradeDatabase

from .migration_cli import MigrationCLI
from .migration_mode import MigrationMode

__all__ = ["MigrationCLI", "MigrationMode", "main"]


def main(arguments: Sequence[str] | None = None) -> int:
    cli_arguments = list(sys.argv[1:] if arguments is None else arguments)
    try:
        settings = PostgresSettings()
        runtime = AlembicRuntime(settings)
        cli = MigrationCLI(
            upgrade=UpgradeDatabase(runtime).execute,
            status=InspectMigrationStatus(runtime).execute,
            output=sys.stdout,
        )
        return cli.dispatch(cli_arguments)
    except Exception as error:
        message = MigrationCLI._redact(str(error))
        sys.stdout.write(f"error: {message}\n")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
