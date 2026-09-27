import asyncio
from unittest.mock import AsyncMock, Mock

from harness_memory_mcp.services.admin_token_verifier import AdminTokenVerifier
from harness_memory_mcp.services.authenticated_principal_factory import (
    AuthenticatedPrincipalFactory,
)
from harness_memory_mcp.services.component_scope_policy import ComponentScopePolicy
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def test_admin_token_verifier_grants_unscoped_admin_and_delegates_other_tokens():
    delegate = Mock(verify_token=AsyncMock(return_value="ordinary-principal"))
    verifier = AdminTokenVerifier(delegate, "admin-secret")
    admin = asyncio.run(verifier.verify_token("admin-secret"))
    assert admin.claims["tenant_id"] == "*"
    assert admin.claims["is_admin"] is True
    assert set(admin.scopes) == {"memory:read", "memory:impact", "memory:publish"}
    principal = AuthenticatedPrincipalFactory().from_verified_claims(admin.claims)
    assert principal.is_admin is True
    assert principal.tenant_id == "*"
    assert (
        AuthenticatedPrincipalFactory("custom_tenant").from_verified_claims(admin.claims).is_admin
        is True
    )
    policy = ComponentScopePolicy()
    assert policy.can_access(principal, "tool", "search_entities")
    assert not policy.can_access(principal, "tool", "publish_project_snapshot")
    context = TenantContextProvider()
    with context.bind_principal(principal):
        assert context.require().is_admin is True
    assert asyncio.run(verifier.verify_token("user-secret")) == "ordinary-principal"
    delegate.verify_token.assert_awaited_once_with("user-secret")


def test_read_api_key_verifier_limits_static_key_to_read_scope():
    delegate = Mock(verify_token=AsyncMock(return_value="ordinary-principal"))
    verifier = AdminTokenVerifier(delegate, " admin-secret ", " read-secret ")

    reader = asyncio.run(verifier.verify_token("read-secret"))
    principal = AuthenticatedPrincipalFactory().from_verified_claims(reader.claims)

    assert reader.claims["tenant_id"] == "*"
    assert set(reader.scopes) == {"memory:read"}
    assert principal.is_admin is True
    assert ComponentScopePolicy().can_access(principal, "tool", "search_entities")
    assert not ComponentScopePolicy().can_access(principal, "tool", "analyze_impact")
    assert asyncio.run(verifier.verify_token("user-secret")) == "ordinary-principal"
    delegate.verify_token.assert_awaited_once_with("user-secret")
