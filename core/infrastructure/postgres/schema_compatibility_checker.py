from core.domain.platform.schema_compatibility_status import SchemaCompatibilityStatus
from core.infrastructure.postgres.alembic_runtime import AlembicRuntime


class SchemaCompatibilityChecker:
    """Inspects database schema revision against Alembic head without executing migrations."""

    def check(self, runtime: AlembicRuntime) -> SchemaCompatibilityStatus:
        status = runtime.status()
        return SchemaCompatibilityStatus(
            current_revision=status.current_revision,
            head_revision=status.head_revision,
        )
