from .alembic_runtime import AlembicRuntime
from .migrations_status import MigrationStatus


class UpgradeDatabase:
    def __init__(self, runtime: AlembicRuntime):
        self.runtime = runtime

    def execute(self) -> MigrationStatus:
        return self.runtime.upgrade("head")
