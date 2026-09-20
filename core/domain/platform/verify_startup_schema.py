from core.domain.platform.schema_compatibility_status import SchemaCompatibilityStatus
from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError
from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.schema_compatibility_checker import SchemaCompatibilityChecker


class VerifyStartupSchema:
    """Verifies that the database schema matches the expected Alembic head revision."""

    def __init__(self, checker: SchemaCompatibilityChecker | None = None):
        self._checker = checker or SchemaCompatibilityChecker()

    def execute(self, runtime: AlembicRuntime) -> SchemaCompatibilityStatus:
        status = self._checker.check(runtime)
        if not status.is_compatible():
            raise SchemaIncompatibleError(status.current_revision, status.head_revision)
        return status
