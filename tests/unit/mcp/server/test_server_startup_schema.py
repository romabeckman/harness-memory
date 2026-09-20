from unittest.mock import MagicMock
import pytest
from core.domain.platform.schema_incompatible_error import SchemaIncompatibleError
from core.infrastructure.postgres.migrations_status import MigrationStatus
from mcp.config import RuntimeSettings
from mcp.server.factory import create_mcp_server


def test_production_server_refuses_startup_when_schema_incompatible():
    mock_runtime = MagicMock()
    mock_runtime.status.return_value = MigrationStatus(
        current_revision="0001",
        head_revision="0002",
    )
    mock_checker = MagicMock()
    mock_checker.check.return_value = MagicMock(is_compatible=lambda: False, current_revision="0001", head_revision="0002")

    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/.well-known/jwks.json",
        mcp_audience="harness-memory",
        mcp_production=True,
        database_url="postgresql://user:pass@localhost:5432/harness_memory",
    )

    with pytest.raises(SchemaIncompatibleError):
        create_mcp_server(
            settings=settings,
            production=True,
            verify_schema=True,
            schema_checker=mock_checker,
            alembic_runtime=mock_runtime,
        )


def test_in_process_server_retains_bypass_mechanism():
    server = create_mcp_server(production=False, verify_schema=False)
    assert server is not None
