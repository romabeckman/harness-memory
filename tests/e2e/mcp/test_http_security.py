from types import SimpleNamespace

from fastmcp.server.auth import AccessToken, TokenVerifier
from starlette.testclient import TestClient

from core.application.entity_discovery.use_cases.search_entities.inbound import SearchEntitiesInput
from core.application.tenant_security.ports.security_audit_repository import AppendResult
from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.server.factory import create_mcp_server


class StaticTokenVerifier(TokenVerifier):
    async def verify_token(self, token):
        if token not in {"read", "publish"}:
            return None
        scope = "memory:read" if token == "read" else "memory:publish"
        return AccessToken(
            token=token,
            client_id="subject-a",
            scopes=[scope],
            subject="subject-a",
            claims={"sub": "subject-a", "tenant_id": "tenant-a", "scope": scope},
        )


def _server_and_records():
    records = []
    repository = SimpleNamespace(
        append=lambda record: records.append(record) or AppendResult(record.event_id)
    )
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/.well-known/jwks.json",
        mcp_audience="harness-memory",
        mcp_production=True,
    )
    server = create_mcp_server(
        settings=settings,
        production=True,
        token_verifier=StaticTokenVerifier(),
        audit_repository=repository,
    )

    @server.tool(name="publish_project_snapshot")
    def publish_project_snapshot():
        return {"ok": True}

    return server, records


def _initialize(client, token=None):
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "security-test", "version": "1"},
            },
        },
        headers=headers,
    )
    return response


def test_http_missing_bearer_returns_401_and_audits_authentication_failure():
    server, records = _server_and_records()
    with TestClient(server.http_app()) as client:
        response = _initialize(client)

    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")
    assert records[-1].event_type.value == "authentication_failure"
    assert records[-1].tenant_id is None
    assert records[-1].subject is None


def test_http_scope_filtering_and_direct_authorization_return_403():
    server, records = _server_and_records()
    with TestClient(server.http_app()) as client:
        initialized = _initialize(client, "read")
        session_id = initialized.headers["mcp-session-id"]
        headers = {"Authorization": "Bearer read", "Mcp-Session-Id": session_id}
        listed = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            headers=headers,
        )
        denied = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "publish_project_snapshot", "arguments": {}},
            },
            headers=headers,
        )

    assert listed.status_code == 200
    assert b"publish_project_snapshot" not in listed.content
    assert denied.status_code == 403
    assert b"insufficient" in denied.content.lower()
    assert denied.headers["www-authenticate"] == (
        'Bearer error="insufficient_scope", scope="memory:publish"'
    )
    assert records[-1].event_type.value == "authorization_failure"


def test_http_invalid_token_uses_same_secret_free_response_as_missing_token():
    server, records = _server_and_records()
    with TestClient(server.http_app()) as client:
        missing = _initialize(client)
        invalid = _initialize(client, "not-valid")

    assert missing.status_code == invalid.status_code == 401
    assert missing.headers["www-authenticate"] == invalid.headers["www-authenticate"]
    assert missing.json() == invalid.json()
    assert all(secret not in invalid.text for secret in ("not-valid", "digest"))
    assert (
        len([record for record in records if record.event_type.value == "authentication_failure"])
        == 2
    )


def test_http_rejects_payload_tenant_override_before_tool_execution():
    server, _records = _server_and_records()
    calls = []

    @server.tool(name="search_entities")
    def search_entities(request: SearchEntitiesInput):
        calls.append(request)
        return {"ok": True}

    with TestClient(server.http_app()) as client:
        initialized = _initialize(client, "read")
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "search_entities",
                    "arguments": {"request": {"key": "payments", "tenant_id": "tenant-b"}},
                },
            },
            headers={
                "Authorization": "Bearer read",
                "Mcp-Session-Id": initialized.headers["mcp-session-id"],
            },
        )

    assert response.status_code == 200
    assert b"INVALID_ARGUMENT" in response.content
    assert b"tenant_id" in response.content
    assert b'"isError":true' in response.content.replace(b" ", b"")
    assert calls == []


def test_http_stateless_tools_can_be_called_without_initialization():
    server, _records = _server_and_records()

    @server.tool(name="search_entities")
    def search_entities():
        return {"entities": []}

    with TestClient(server.http_app(stateless_http=True)) as client:
        response = client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": "search_entities", "arguments": {}},
            },
            headers={"Authorization": "Bearer read"},
        )

    assert response.status_code == 200
    assert b"entities" in response.content
    assert b"Missing session ID" not in response.content
