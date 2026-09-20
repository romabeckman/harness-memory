from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

from fastmcp.server.auth import TokenVerifier
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from api.application.services.token_service import TokenService
from api.application.services.user_service import UserService
from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository
from mcp.config import RuntimeSettings
from mcp.server.factory import create_mcp_server
from mcp.services.database_token_verifier import DatabaseTokenVerifier


def test_api_issued_token_authenticates_mcp_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine, tables=[ApiUser.__table__, ApiAccessToken.__table__])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    users = ApiUserRepository(factory)
    tokens = ApiTokenRepository(factory)
    user = UserService(users).create("Ada", "ada@example.com")
    issued = TokenService(tokens, users).create(
        user_id=user.id,
        name="mcp-client",
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    audit_records = []
    audit_repository = SimpleNamespace(
        append=lambda record: audit_records.append(record) or AppendResult(record.event_id)
    )
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/jwks",
        mcp_audience="harness-memory",
        mcp_production=True,
    )
    verifier: TokenVerifier = DatabaseTokenVerifier(tokens)
    server = create_mcp_server(
        settings,
        production=True,
        token_verifier=verifier,
        audit_repository=audit_repository,
        handler=Mock(),
        verify_schema=False,
    )

    with TestClient(server.http_app()) as client:
        response = client.post(
            "/mcp",
            headers={"Authorization": f"Bearer {issued.plaintext}"},
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "api-token-test", "version": "1"},
                },
            },
        )

    assert response.status_code == 200
