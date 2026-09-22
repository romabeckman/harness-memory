import asyncio
from datetime import UTC, datetime
from hashlib import sha256

from fastmcp.server.auth import AccessToken, TokenVerifier

from api.application.ports.token_repository import TokenRepository


class DatabaseTokenVerifier(TokenVerifier):
    def __init__(self, repository: TokenRepository) -> None:
        super().__init__(required_scopes=None)
        self._repository = repository

    async def verify_token(self, token: str) -> AccessToken | None:
        if not isinstance(token, str) or not token.strip():
            return None
        token_hash = sha256(token.encode()).hexdigest()
        identity = await asyncio.to_thread(
            self._repository.find_active_by_hash,
            token_hash,
            now=datetime.now(UTC),
        )
        if identity is None:
            return None
        stored, owner = identity
        owner_id = getattr(owner, "id", None)
        owner_tenant_id = getattr(owner, "tenant_id", None)
        if stored is None or owner_id is None or owner_tenant_id is None:
            return None
        subject = str(owner_id)
        tenant_id = str(owner_tenant_id)
        scopes = sorted(stored.scopes)
        return AccessToken(
            token=token,
            client_id=subject,
            scopes=scopes,
            expires_at=(
                int(stored.expires_at.timestamp()) if stored.expires_at is not None else None
            ),
            subject=subject,
            claims={
                "sub": subject,
                "tenant_id": tenant_id,
                "scope": " ".join(scopes),
            },
        )
