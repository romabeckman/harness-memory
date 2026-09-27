from uuid import UUID, uuid4

from api.application.ports.service_account_repository import ServiceAccountRepository
from api.domain.entities.service_account import ServiceAccount


class ServiceAccountService:
    def __init__(self, repository: ServiceAccountRepository) -> None:
        self._repository = repository

    def create(self, name: str, tenant_id: UUID) -> ServiceAccount:
        normalized_name = self._normalize_name(name)
        return self._repository.add(ServiceAccount(uuid4(), tenant_id, normalized_name))

    def get(self, account_id: UUID) -> ServiceAccount:
        account = self._repository.get(account_id)
        if account is None:
            raise LookupError("service account not found")
        return account

    def list(
        self,
        tenant_id: UUID | None = None,
        *,
        name: str | None = None,
        q: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> list[ServiceAccount]:
        if name is None and q is None and limit is None and offset is None:
            return self._repository.list(tenant_id)
        return self._repository.list(
            tenant_id,
            name=name,
            q=q,
            limit=limit if limit is not None else 100,
            offset=offset if offset is not None else 0,
        )

    def update(self, account_id: UUID, *, name: str | None) -> ServiceAccount:
        account = self.get(account_id)
        if name is not None:
            account.name = self._normalize_name(name)
        return self._repository.update(account)

    def delete(self, account_id: UUID) -> None:
        self.get(account_id)
        self._repository.delete(account_id)

    @staticmethod
    def _normalize_name(name: str) -> str:
        value = name.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value
