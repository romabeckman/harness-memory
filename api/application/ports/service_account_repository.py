from typing import Protocol
from uuid import UUID

from api.domain.entities.service_account import ServiceAccount


class ServiceAccountRepository(Protocol):
    def add(self, account: ServiceAccount) -> ServiceAccount: ...

    def get(self, account_id: UUID) -> ServiceAccount | None: ...

    def list(
        self,
        tenant_id: UUID | None = None,
        *,
        name: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ServiceAccount]: ...

    def update(self, account: ServiceAccount) -> ServiceAccount: ...

    def delete(self, account_id: UUID) -> None: ...
