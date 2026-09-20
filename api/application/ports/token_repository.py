from datetime import datetime
from typing import Protocol
from uuid import UUID

from api.domain.entities.access_token import AccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User


class TokenRepository(Protocol):
    def add(self, token: AccessToken) -> AccessToken: ...

    def get(self, token_id: UUID) -> AccessToken | None: ...

    def list(
        self,
        user_id: UUID | None = None,
        service_account_id: UUID | None = None,
    ) -> list[AccessToken]: ...

    def update(self, token: AccessToken) -> AccessToken: ...

    def delete(self, token_id: UUID) -> None: ...

    def find_active_by_hash(
        self, token_hash: str, *, now: datetime
    ) -> tuple[AccessToken, User | ServiceAccount] | None: ...
