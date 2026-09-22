from hmac import compare_digest

from fastmcp.server.auth import AccessToken, TokenVerifier

from core.domain.tenant_security.value_objects.authenticated_principal import ADMIN_TENANT_ID


class AdminTokenVerifier(TokenVerifier):
    def __init__(self, delegate: TokenVerifier, admin_token: str) -> None:
        super().__init__(required_scopes=None)
        self._delegate = delegate
        self._admin_token = admin_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not isinstance(token, str) or not compare_digest(token, self._admin_token):
            return await self._delegate.verify_token(token)
        return admin_access_token(token)


def admin_access_token(token: str) -> AccessToken:
    """Create global admin identity; MCP component scope checks still apply."""
    scopes = ["memory:read", "memory:impact", "memory:publish"]
    return AccessToken(
        token=token,
        client_id="admin",
        scopes=scopes,
        subject="admin",
        claims={
            "sub": "admin",
            "tenant_id": ADMIN_TENANT_ID,
            "is_admin": True,
            "scope": " ".join(scopes),
        },
    )
