from hmac import compare_digest

from fastmcp.server.auth import AccessToken, TokenVerifier

from core.domain.tenant_security.value_objects.authenticated_principal import ADMIN_TENANT_ID


class AdminTokenVerifier(TokenVerifier):
    def __init__(
        self,
        delegate: TokenVerifier,
        admin_token: str | None,
        read_api_key: str | None = None,
    ) -> None:
        super().__init__(required_scopes=None)
        self._delegate = delegate
        self._admin_token = admin_token.strip() if admin_token else None
        self._read_api_key = read_api_key.strip() if read_api_key else None
        self.logger = getattr(delegate, "logger", None)

    async def verify_token(self, token: str) -> AccessToken | None:
        if not isinstance(token, str):
            return None
        if self._admin_token and compare_digest(token, self._admin_token):
            return admin_access_token(token)
        if self._read_api_key and compare_digest(token, self._read_api_key):
            return read_access_token(token)
        return await self._delegate.verify_token(token)


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


def read_access_token(token: str) -> AccessToken:
    """Create global read-only identity for the configured API read key."""
    return AccessToken(
        token=token,
        client_id="read-api-key",
        scopes=["memory:read"],
        subject="read-api-key",
        claims={
            "sub": "read-api-key",
            "tenant_id": ADMIN_TENANT_ID,
            "is_admin": True,
            "scope": "memory:read",
        },
    )
