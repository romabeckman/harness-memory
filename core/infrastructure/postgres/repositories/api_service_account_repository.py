from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.domain.entities.service_account import ServiceAccount
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount


class ApiServiceAccountRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, account: ServiceAccount) -> ServiceAccount:
        with self._session_factory() as session:
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

    def list(self, tenant_id: UUID | None = None) -> list[ServiceAccount]:
        statement = select(ApiServiceAccount).order_by(ApiServiceAccount.name)
        if tenant_id is not None:
            statement = statement.where(ApiServiceAccount.tenant_id == tenant_id)
        with self._session_factory() as session:
            return [self._to_domain(row) for row in session.scalars(statement).all()]

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
