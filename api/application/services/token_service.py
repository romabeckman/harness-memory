from datetime import UTC, datetime
from hashlib import sha256
from secrets import token_urlsafe
from uuid import UUID, uuid4

from api.application.ports.service_account_repository import ServiceAccountRepository
from api.application.ports.tenant_project_management_repository import (
    TenantProjectManagementRepository,
)
from api.application.ports.token_repository import TokenRepository
from api.application.ports.user_repository import UserRepository
from api.domain.entities.access_token import AccessToken
from api.domain.entities.issued_token import IssuedToken
from api.domain.services.token_expiration_policy import TokenExpirationPolicy
from core.domain.tenant_security.types.memory_scope import MemoryScope


class TokenService:
    def __init__(
        self,
        repository: TokenRepository,
        user_repository: UserRepository,
        expiration_policy: TokenExpirationPolicy | None = None,
        *,
        service_account_repository: ServiceAccountRepository | None = None,
        project_repository: TenantProjectManagementRepository | None = None,
    ) -> None:
        self._repository = repository
        self._user_repository = user_repository
        self._service_account_repository = service_account_repository
        self._project_repository = project_repository
        self._expiration_policy = expiration_policy or TokenExpirationPolicy()

    def create(
        self,
        *,
        user_id: UUID | None = None,
        service_account_id: UUID | None = None,
        name: str,
        expires_at: datetime | None = None,
        scopes: set[str] | frozenset[str] | None = None,
        project_keys: list[str] | set[str] | frozenset[str] | None = None,
        now: datetime | None = None,
    ) -> IssuedToken:
        if (user_id is None) == (service_account_id is None):
            raise ValueError("exactly one token owner is required")
        if user_id is not None:
            user = self._user_repository.get(user_id)
            if user is None:
                raise LookupError("user not found")
            if expires_at is None:
                raise ValueError("user tokens require an expiration")
        elif self._service_account_repository is None:
            raise LookupError("service account not found")
        else:
            sa = self._service_account_repository.get(service_account_id)
            if sa is None:
                raise LookupError("service account not found")

        cleaned_projects = [
            k.strip()
            for k in (project_keys or ())
            if isinstance(k, str) and k.strip()
        ]
        if not cleaned_projects:
            raise ValueError("at least one project is required")
        normalized_projects = list(dict.fromkeys(cleaned_projects))
        if "*" in normalized_projects:
            normalized_projects = ["*"]

        normalized_name = self._normalize_name(name)
        created_at = self._as_utc(now or datetime.now(UTC))
        expiration = (
            self._expiration_policy.validate(expires_at, now=created_at, issued_at=created_at)
            if expires_at is not None
            else None
        )

        if self._project_repository is not None and "*" not in normalized_projects:
            for pkey in normalized_projects:
                proj = self._project_repository.get_project_by_key(pkey)
                if proj is None:
                    raise LookupError(f"project '{pkey}' not found")
        token_id = uuid4()
        normalized_scopes = frozenset(scopes or {MemoryScope.READ.value})
        supported_scopes = {scope.value for scope in MemoryScope}
        if not normalized_scopes or not normalized_scopes <= supported_scopes:
            raise ValueError("unsupported token scope")
        plaintext = f"hm_{token_id.hex}.{token_urlsafe(32)}"
        token = AccessToken(
            id=token_id,
            user_id=user_id,
            service_account_id=service_account_id,
            name=normalized_name,
            token_hash=sha256(plaintext.encode()).hexdigest(),
            expires_at=expiration,
            created_at=created_at,
            scopes=normalized_scopes,
            allowed_project_keys=frozenset(normalized_projects),
        )
        return IssuedToken(self._repository.add(token), plaintext)

    def get(self, token_id: UUID) -> AccessToken:
        token = self._repository.get(token_id)
        if token is None:
            raise LookupError("token not found")
        return token

    def list(
        self,
        user_id: UUID | None = None,
        service_account_id: UUID | None = None,
    ) -> list[AccessToken]:
        return self._repository.list(user_id, service_account_id)

    def update(
        self,
        token_id: UUID,
        *,
        name: str | None,
        expires_at: datetime | None,
        now: datetime | None = None,
    ) -> AccessToken:
        token = self.get(token_id)
        if name is not None:
            token.name = self._normalize_name(name)
        if expires_at is not None:
            token.expires_at = self._expiration_policy.validate(
                expires_at,
                now=now,
                issued_at=token.created_at,
            )
        return self._repository.update(token)

    def delete(self, token_id: UUID) -> None:
        self.get(token_id)
        self._repository.delete(token_id)

    @staticmethod
    def _normalize_name(name: str) -> str:
        value = name.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
