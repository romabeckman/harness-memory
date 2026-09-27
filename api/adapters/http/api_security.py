from datetime import UTC, datetime
from hashlib import sha256
from hmac import compare_digest

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.application.ports.token_repository import TokenRepository
from api.domain.entities.access_token import AccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User
from core.domain.tenant_security.value_objects.authenticated_principal import (
    ADMIN_TENANT_ID,
    AuthenticatedPrincipal,
)

_bearer = HTTPBearer(auto_error=False)


class ApiSecurity:
    def __init__(
        self,
        token_repository: TokenRepository,
        admin_token: str | None,
        read_api_key: str | None = None,
    ) -> None:
        self._token_repository = token_repository
        self._admin_token = admin_token.strip() if admin_token else None
        self._read_api_key = read_api_key.strip() if read_api_key else None

    def require_admin(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> None:
        if self._admin_token is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="API administration is not configured",
            )
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if compare_digest(credentials.credentials, self._admin_token):
            return
        if self._matches_read_key(credentials.credentials):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient scope",
            )
        if self._find_active_token(credentials.credentials) is not None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient scope",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    def require_publisher(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> AuthenticatedPrincipal:
        return self._require_scope(credentials, "memory:publish")

    def require_reader(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> AuthenticatedPrincipal:
        return self._require_scope(credentials, "memory:read")

    def require_baseline_reader(
        self,
        credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    ) -> AuthenticatedPrincipal:
        return self._require_scope(credentials, "memory:read memory:publish")

    def _require_scope(
        self,
        credentials: HTTPAuthorizationCredentials | None,
        required_scope: str,
    ) -> AuthenticatedPrincipal:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if self._admin_token and compare_digest(credentials.credentials, self._admin_token):
            return AuthenticatedPrincipal(
                subject="admin",
                tenant_id=ADMIN_TENANT_ID,
                scopes=frozenset({"memory:read", "memory:impact", "memory:publish"}),
                is_admin=True,
            )
        if self._matches_read_key(credentials.credentials):
            if "memory:read" not in required_scope.split():
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="insufficient scope",
                    headers={"WWW-Authenticate": f'Bearer scope="{required_scope}"'},
                )
            return AuthenticatedPrincipal(
                subject="read-api-key",
                tenant_id=ADMIN_TENANT_ID,
                scopes=frozenset({"memory:read"}),
                is_admin=True,
            )
        identity = self._find_active_token(credentials.credentials)
        if identity is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token, owner = identity
        if not any(scope in token.scopes for scope in required_scope.split()):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="insufficient scope",
                headers={"WWW-Authenticate": f'Bearer scope="{required_scope}"'},
            )
        return AuthenticatedPrincipal(
            subject=str(owner.id),
            tenant_id=str(owner.tenant_id or owner.id),
            scopes=token.scopes,
            allowed_project_keys=token.allowed_project_keys,
        )

    def _find_active_token(
        self, plaintext: str
    ) -> tuple[AccessToken, User | ServiceAccount] | None:
        token_hash = sha256(plaintext.encode()).hexdigest()
        return self._token_repository.find_active_by_hash(token_hash, now=datetime.now(UTC))

    def _matches_read_key(self, plaintext: str) -> bool:
        return bool(self._read_api_key and compare_digest(plaintext, self._read_api_key))
