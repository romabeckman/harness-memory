import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastmcp.server.auth import TokenVerifier
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.testclient import TestClient

from api.application.services.service_account_service import ServiceAccountService
from api.application.services.token_service import TokenService
from api.application.services.user_service import UserService
from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.api_service_account_repository import (
    ApiServiceAccountRepository,
)
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository
from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.database_token_verifier import DatabaseTokenVerifier


def test_api_issued_token_authenticates_mcp_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    users = ApiUserRepository(factory)
    tokens = ApiTokenRepository(factory)
    user = UserService(users).create("Ada", "ada@example.com")
    issued = TokenService(tokens, users).create(
        user_id=user.id,
        name="mcp-client",
        project_keys=["catalog"],
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


def test_service_account_token_authenticates_with_its_bound_tenant():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    accounts = ApiServiceAccountRepository(factory)
    tokens = ApiTokenRepository(factory)
    tenant_id = uuid4()
    account = ServiceAccountService(accounts).create("deployment agent", tenant_id)
    issued = TokenService(
        tokens, ApiUserRepository(factory), service_account_repository=accounts
    ).create(
        service_account_id=account.id,
        name="mcp-client",
        project_keys=["catalog"],
        expires_at=None,
    )

    verified = asyncio.run(DatabaseTokenVerifier(tokens).verify_token(issued.plaintext))

    assert verified is not None
    assert verified.subject == str(account.id)
    assert verified.claims["tenant_id"] == str(tenant_id)
    assert verified.expires_at is None

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
    server = create_mcp_server(
        settings,
        production=True,
        token_verifier=DatabaseTokenVerifier(tokens),
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
                    "clientInfo": {"name": "service-account-token-test", "version": "1"},
                },
            },
        )

    assert response.status_code == 200


def test_admin_mcp_authenticates_without_tenant_header():
    audit_repository = SimpleNamespace(
        append=lambda record: AppendResult(record.event_id)
    )
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/jwks",
        mcp_audience="harness-memory",
        mcp_production=True,
    )
    server = create_mcp_server(
        settings, production=True,
        token_verifier=DatabaseTokenVerifier(Mock(), admin_token="admin-secret"),
        audit_repository=audit_repository, handler=Mock(), verify_schema=False,
    )
    request = {"jsonrpc": "2.0", "id": 1, "method": "initialize",
               "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                          "clientInfo": {"name": "admin-test", "version": "1"}}}
    with TestClient(server.http_app()) as client:
        response = client.post(
            "/mcp", headers={"Authorization": "Bearer admin-secret"}, json=request
        )
    assert response.status_code == 200


def test_admin_mcp_authenticates_in_jwt_mode():
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/jwks",
        mcp_audience="harness-memory",
        mcp_production=True,
        api_admin_token="admin-secret",
    )
    server = create_mcp_server(
        settings, production=True,
        audit_repository=SimpleNamespace(append=lambda record: AppendResult(record.event_id)),
        handler=Mock(), verify_schema=False,
    )
    with TestClient(server.http_app()) as client:
        response = client.post("/mcp", headers={"Authorization": "Bearer admin-secret"},
            json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                             "clientInfo": {"name": "jwt-admin-test", "version": "1"}}})
    assert response.status_code == 200
