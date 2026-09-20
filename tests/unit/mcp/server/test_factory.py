from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.database_token_verifier import DatabaseTokenVerifier
from harness_memory_mcp.services.security_audit_middleware import AuditingTokenVerifier


def test_create_mcp_server_is_named_and_database_independent():
    server = create_mcp_server(
        RuntimeSettings(mcp_host="127.0.0.1", mcp_port=8000, database_url=None)
    )

    assert server.name == "harness-memory"


def test_create_mcp_server_uses_api_token_repository_in_database_auth_mode():
    repository = object()
    settings = RuntimeSettings(
        mcp_auth_mode="database",
        database_url="postgresql+psycopg2://user:pass@postgres/memory",
        mcp_production=True,
    )

    server = create_mcp_server(
        settings,
        production=True,
        api_token_repository=repository,
        audit_handler=object(),
        handler=object(),
        verify_schema=False,
    )

    assert isinstance(server.auth, AuditingTokenVerifier)
    assert isinstance(server.auth.verifier, DatabaseTokenVerifier)
