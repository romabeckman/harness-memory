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
        if cli_arguments and cli_arguments[0] == "publish":
            from core.application.knowledge_publication.use_cases.publish_knowledge.handler import (
                PublishKnowledgeHandler,
            )
            from core.infrastructure.postgres.engine_factory import PostgresEngineFactory
            from core.infrastructure.postgres.repositories.environment_repository import (
                PostgresEnvironmentRepository,
            )
            from core.infrastructure.postgres.repositories.knowledge_publication_repository import (
                PostgresKnowledgePublicationRepository,
            )
            from .publication_cli import PublicationCLI

            engine = PostgresEngineFactory.create(settings)
            env_repo = PostgresEnvironmentRepository(engine=engine)
            pub_repo = PostgresKnowledgePublicationRepository(engine=engine)
            handler = PublishKnowledgeHandler(
                publication_repository=pub_repo,
                environment_repository=env_repo,
            )
            pub_cli = PublicationCLI(publish=handler.execute, output=sys.stdout)
            return pub_cli.dispatch(cli_arguments)

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
