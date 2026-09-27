from collections.abc import Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.domain.entities.service_account import ServiceAccount
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount


class ApiServiceAccountRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, account: ServiceAccount) -> ServiceAccount:
        with self._session_factory() as session:
            try:
                from core.infrastructure.postgres.models.tenant import Tenant

                tenant = session.get(Tenant, account.tenant_id)
                if tenant is None or tenant.status != "active":
                    raise ValueError("tenant not found or disabled")
            except ValueError:
                raise
            except Exception:
                pass
            session.add(
                ApiServiceAccount(
                    id=account.id,
                    tenant_id=account.tenant_id,
                    name=account.name,
                )
            )
            session.commit()
        return account

    def get(self, account_id: UUID) -> ServiceAccount | None:
        with self._session_factory() as session:
            return self._to_domain(session.get(ApiServiceAccount, account_id))

    def list(
        self,
        tenant_id: UUID | None = None,
        *,
        name: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ServiceAccount]:
        statement = select(ApiServiceAccount)
        if tenant_id is not None:
            statement = statement.where(ApiServiceAccount.tenant_id == tenant_id)
        if name:
            statement = statement.where(self._contains(ApiServiceAccount.name, name))
        if q:
            statement = statement.where(self._contains(ApiServiceAccount.name, q))
        with self._session_factory() as session:
            rows = session.scalars(
                statement.order_by(ApiServiceAccount.name).limit(limit).offset(offset)
            ).all()
            return [self._to_domain(row) for row in rows]

    @staticmethod
    def _contains(column, value: str):
        escaped = value.casefold().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        return func.lower(column).like(f"%{escaped}%", escape="\\")

    def update(self, account: ServiceAccount) -> ServiceAccount:
        with self._session_factory() as session:
            row = session.get(ApiServiceAccount, account.id)
            if row is None:
                raise LookupError("service account not found")
            row.name = account.name
            session.commit()
        return account

    def delete(self, account_id: UUID) -> None:
        with self._session_factory() as session:
            row = session.get(ApiServiceAccount, account_id)
            if row is not None:
                session.delete(row)
                session.commit()

    @staticmethod
    def _to_domain(row: ApiServiceAccount | None) -> ServiceAccount | None:
        if row is None:
            return None
        return ServiceAccount(id=row.id, tenant_id=row.tenant_id, name=row.name)
