from collections.abc import Mapping

from core.domain.tenant_security.value_objects.authenticated_principal import (
    ADMIN_TENANT_ID,
    AuthenticatedPrincipal,
)


class AuthenticatedPrincipalFactory:
    def __init__(self, tenant_claim: str = "tenant_id"):
        if not isinstance(tenant_claim, str) or not tenant_claim.strip():
            raise ValueError("tenant claim name is required")
        self.tenant_claim = tenant_claim.strip()

    def from_verified_claims(self, claims: Mapping[str, object]) -> AuthenticatedPrincipal:
        if not isinstance(claims, Mapping):
            raise ValueError("verified token claims are required")
        subject = claims.get("sub")
        is_admin = claims.get("is_admin") is True
        tenant = claims.get(self.tenant_claim, ADMIN_TENANT_ID if is_admin else None)
        if not isinstance(subject, str) or not subject.strip():
            raise ValueError("verified token subject is required")
        if not isinstance(tenant, str) or not tenant.strip():
            raise ValueError("verified token tenant is required")
        raw_scopes = claims.get("scope", "")
        if isinstance(raw_scopes, str):
            scopes = raw_scopes.split()
        elif isinstance(raw_scopes, (list, tuple, set, frozenset)):
            scopes = [scope for scope in raw_scopes if isinstance(scope, str)]
        else:
            scopes = []
        return AuthenticatedPrincipal(subject.strip(), tenant.strip(), frozenset(scopes), is_admin)

    from_claims = from_verified_claims
