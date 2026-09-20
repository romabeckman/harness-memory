import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastmcp.server.auth import AccessToken, TokenVerifier

from core.application.tenant_security.ports.security_audit_repository import AppendResult
from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal
from mcp.config import RuntimeSettings, SecuritySettings
from mcp.services.audited_operation import AuditPersistenceFailure, ExecuteAuditedOperation
from mcp.services.authenticated_principal_factory import AuthenticatedPrincipalFactory
from mcp.services.component_scope_policy import ComponentScopePolicy, component_scope_auth
from mcp.services.request_security_context import RequestSecurityContext
from mcp.services.security_audit_middleware import (
    AuditingTokenVerifier,
    SecurityAuditMiddleware,
)
from mcp.services.security_failure_mapper import SecurityFailureMapper
from mcp.services.tenant_context import TenantContextProvider


class Repo:
    def __init__(self, fail=False):
        self.fail = fail
        self.records = []

    def append(self, record):
        if self.fail:
            raise RuntimeError("database password=secret")
        self.records.append(record)
        return AppendResult(record.event_id)


def principal(tenant="tenant-a", scopes=("memory:read",)):
    return AuthenticatedPrincipal("subject-a", tenant, frozenset(scopes))


def test_principal_factory_and_scope_policy_are_deny_by_default():
    factory = AuthenticatedPrincipalFactory()
    result = factory.from_verified_claims(
        {"sub": " subject-a ", "tenant_id": " tenant-a ", "scope": "memory:read openid"}
    )
    assert result.tenant_id == "tenant-a"
    policy = ComponentScopePolicy()
    assert policy.required_scope("tool", "publish_project_snapshot") == "memory:publish"
    assert policy.required_scope("tool", "new_component") is None
    assert policy.can_access(result, "tool", "search_entities")
    assert not policy.can_access(result, "tool", "publish_project_snapshot")
    with pytest.raises(PermissionError):
        policy.authorize(result, "tool", "new_component")
    with pytest.raises(PermissionError):
        policy.authorize(result, "tool", "publish_project_snapshot")
    with pytest.raises(ValueError):
        factory.from_verified_claims({"sub": "subject-a", "tenant_id": " "})

    assert policy.required_scope("resource", "memory://entities/123") == "memory:read"
    assert policy.required_scope("resource", "memory://projects/payments") == "memory:read"
    assert policy.required_scope("resource", "memory://snapshots/123") == "memory:read"
    assert policy.required_scope("prompt", "review_change_impact") == "memory:impact"
    assert policy.filter_components(
        result,
        "tool",
        [SimpleNamespace(name="search_entities"), SimpleNamespace(name="publish_project_snapshot")],
    )[0].name == "search_entities"


def test_request_context_is_reset_for_success_failure_and_concurrency():
    context = RequestSecurityContext()
    first = principal()
    second = principal("tenant-b", ("memory:impact",))

    def success():
        assert context.require() is first
        return "ok"

    assert context.bind(first, success) == "ok"
    with pytest.raises(RuntimeError):
        context.require()

    async def run(item):
        with context.bind(item):
            await asyncio.sleep(0)
            return context.require().tenant_id

    async def concurrent():
        return await asyncio.gather(run(first), run(second))

    assert asyncio.run(concurrent()) == ["tenant-a", "tenant-b"]


def test_audited_operation_blocks_on_attempt_and_records_completion():
    repo = Repo()
    audited = ExecuteAuditedOperation(RecordSecurityAuditHandler(repo))
    seen = []
    result = audited.execute(
        operation=lambda: seen.append("called") or {"ok": True},
        principal=principal(scopes=("memory:publish",)),
        request_id=uuid4(),
        event_type="publication",
        component="publish_project_snapshot",
        required_scope="memory:publish",
        safe_details={"project_key": "payments"},
    )
    assert result == {"ok": True}
    assert seen == ["called"]
    assert [record.phase.value for record in repo.records] == ["attempted", "completed"]

    blocked = ExecuteAuditedOperation(RecordSecurityAuditHandler(Repo(fail=True)))
    with pytest.raises(AuditPersistenceFailure):
        blocked.execute(
            operation=lambda: seen.append("bad"),
            principal=principal(scopes=("memory:publish",)),
            request_id=uuid4(),
            event_type="publication",
            component="publish_project_snapshot",
            required_scope="memory:publish",
        )
    assert seen == ["called"]


def test_security_failure_mapper_returns_safe_challenges():
    mapper = SecurityFailureMapper()
    auth = mapper.authentication()
    forbidden = mapper.authorization("memory:publish")
    assert auth.status_code == 401
    assert auth.headers["WWW-Authenticate"].startswith("Bearer")
    assert forbidden.status_code == 403
    assert forbidden.code == "insufficient_scope"


def test_component_auth_uses_exact_scopes_and_security_settings_validate():
    policy = ComponentScopePolicy()
    token = SimpleNamespace(
        scopes=["memory:read"],
        claims={"sub": "subject-a", "tenant_id": "tenant-a"},
    )
    assert component_scope_auth(policy)(
        SimpleNamespace(token=token, component=SimpleNamespace(name="search_entities"))
    )
    assert not component_scope_auth(policy)(
        SimpleNamespace(token=token, component=SimpleNamespace(name="publish_project_snapshot"))
    )
    with pytest.raises(ValueError):
        SecuritySettings(
            issuer="https://issuer.example",
            jwks_uri="https://issuer.example/jwks",
            audience=" ",
        )
    settings = RuntimeSettings(
        mcp_issuer="https://issuer.example",
        mcp_jwks_uri="https://issuer.example/jwks",
        mcp_audience="aud",
        mcp_production=True,
    )
    assert settings.security is not None


def test_security_middleware_binds_typed_requests_and_filters_catalog(monkeypatch):
    import mcp.services.security_audit_middleware as middleware_module

    repository = Repo()
    tenant_context = TenantContextProvider()
    middleware = SecurityAuditMiddleware(
        tenant_context,
        AuthenticatedPrincipalFactory(),
        audit_handler=RecordSecurityAuditHandler(repository),
    )
    token = AccessToken(
        token="token",
        client_id="subject-a",
        scopes=["memory:read"],
        subject="subject-a",
        claims={"sub": "subject-a", "tenant_id": "tenant-a", "scope": "memory:read"},
    )
    monkeypatch.setattr(middleware_module, "get_access_token", lambda: token)

    async def call_next(_):
        return [
            SimpleNamespace(name="search_entities"),
            SimpleNamespace(name="publish_project_snapshot"),
        ]

    async def run():
        tools = await middleware.on_list_tools(SimpleNamespace(), call_next)
        assert [tool.name for tool in tools] == ["search_entities"]
        await middleware.on_call_tool(
            SimpleNamespace(message=SimpleNamespace(name="publish_project_snapshot")),
            call_next,
        )

    asyncio.run(run())
    assert repository.records[-1].reason_code == "insufficient_scope"
    assert tenant_context.security_context.current() is None


def test_auditing_token_verifier_records_invalid_and_accepts_valid():
    class Verifier(TokenVerifier):
        async def verify_token(self, token):
            if token == "bad":
                return None
            return AccessToken(
                token=token,
                client_id="subject-a",
                scopes=["memory:read"],
                subject="subject-a",
                claims={"sub": "subject-a", "tenant_id": "tenant-a", "scope": "memory:read"},
            )

    repository = Repo()
    verifier = AuditingTokenVerifier(
        Verifier(),
        RecordSecurityAuditHandler(repository),
        AuthenticatedPrincipalFactory(),
    )

    async def run():
        assert await verifier.verify_token("bad") is None
        assert (await verifier.verify_token("good")).subject == "subject-a"

    asyncio.run(run())
    assert repository.records[0].event_type.value == "authentication_failure"
