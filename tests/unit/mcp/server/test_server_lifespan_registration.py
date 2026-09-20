from types import SimpleNamespace
from unittest.mock import MagicMock

from starlette.testclient import TestClient

from mcp.config import RuntimeSettings
from mcp.server.factory import create_mcp_server
from core.infrastructure.postgres.migrations_status import MigrationStatus


def test_production_server_registers_schema_lifespan_when_verification_is_deferred():
    runtime = MagicMock()
    runtime.status.return_value = MigrationStatus(current_revision="0002", head_revision="0002")
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/.well-known/jwks.json",
        mcp_audience="harness-memory",
        mcp_production=True,
    )

    server = create_mcp_server(
        settings=settings,
        production=True,
        verify_schema=False,
        alembic_runtime=runtime,
        audit_handler=SimpleNamespace(execute=lambda command: None),
    )

    with TestClient(server.http_app()) as client:
        assert client is not None

    runtime.status.assert_called_once()
