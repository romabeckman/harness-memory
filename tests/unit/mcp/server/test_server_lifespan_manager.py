import asyncio
from unittest.mock import MagicMock

import pytest

from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError
from core.infrastructure.postgres.migrations_status import MigrationStatus
from harness_memory_mcp.server.server_lifespan_manager import ServerLifespanManager


def test_failed_startup_disposes_runtime_resources():
    runtime = MagicMock()
    runtime.status.return_value = MigrationStatus(current_revision="0001", head_revision="0002")
    engine = MagicMock()
    manager = ServerLifespanManager(alembic_runtime=runtime, engine=engine)

    async def run_lifespan():
        async with manager.lifespan(None):
            pass

    with pytest.raises(SchemaIncompatibleError):
        asyncio.run(run_lifespan())

    engine.dispose.assert_called_once()
    runtime.dispose.assert_called_once()
