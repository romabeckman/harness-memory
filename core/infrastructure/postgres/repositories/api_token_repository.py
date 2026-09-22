from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, sessionmaker

from api.domain.entities.access_token import AccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser


class ApiTokenRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        *,
        engine=None,
    ) -> None:
        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def add(self, token: AccessToken) -> AccessToken:
        with self._session_factory() as session:
            session.add(
                ApiAccessToken(
                    id=token.id,
                    user_id=token.user_id,
                    service_account_id=token.service_account_id,
                    name=token.name,
                    token_hash=token.token_hash,
                    expires_at=token.expires_at,
                    created_at=token.created_at or datetime.now(UTC),
                    scopes=sorted(token.scopes),
                )
            )
            session.commit()
        return token

    def get(self, token_id: UUID) -> AccessToken | None:
        with self._session_factory() as session:
            return self._to_domain(session.get(ApiAccessToken, token_id))

    def list(
        self,
        user_id: UUID | None = None,
        service_account_id: UUID | None = None,
    ) -> list[AccessToken]:
        statement = select(ApiAccessToken).order_by(ApiAccessToken.created_at)
        if user_id is not None:
            statement = statement.where(ApiAccessToken.user_id == user_id)
        if service_account_id is not None:
            statement = statement.where(ApiAccessToken.service_account_id == service_account_id)
        with self._session_factory() as session:
            rows = session.scalars(statement).all()
            return [self._to_domain(row) for row in rows]

    def update(self, token: AccessToken) -> AccessToken:
        with self._session_factory() as session:
            row = session.get(ApiAccessToken, token.id)
            if row is None:
                raise LookupError("token not found")
            row.name = token.name
            row.expires_at = token.expires_at
            session.commit()
        return token

    def delete(self, token_id: UUID) -> None:
        with self._session_factory() as session:
            row = session.get(ApiAccessToken, token_id)
            if row is not None:
                session.delete(row)
                session.commit()

    def find_active_by_hash(
        self, token_hash: str, *, now: datetime
    ) -> tuple[AccessToken, User | ServiceAccount] | None:
        statement = (
            select(ApiAccessToken, ApiUser, ApiServiceAccount)
            .outerjoin(ApiUser, ApiUser.id == ApiAccessToken.user_id)
            .outerjoin(
                ApiServiceAccount,
                ApiServiceAccount.id == ApiAccessToken.service_account_id,
            )
            .where(
                ApiAccessToken.token_hash == token_hash,
                or_(ApiAccessToken.expires_at.is_(None), ApiAccessToken.expires_at > now),
            )
        )
        with self._session_factory() as session:
            row = session.execute(statement).one_or_none()
            if row is None:
                return None
            stored, user, account = row
            if user is not None:
                owner = User(id=user.id, name=user.name, email=user.email)
            elif account is not None:
                owner = ServiceAccount(
                    id=account.id,
                    tenant_id=account.tenant_id,
                    name=account.name,
                )
            else:
                return None
            return self._to_domain(stored), owner

    @staticmethod
    def _to_domain(row: ApiAccessToken | None) -> AccessToken | None:
        if row is None:
            return None
        return AccessToken(
            id=row.id,
            user_id=row.user_id,
            service_account_id=row.service_account_id,
            scopes=frozenset(row.scopes or ()),
            name=row.name,
            token_hash=row.token_hash,
            expires_at=(
                ApiTokenRepository._as_utc(row.expires_at) if row.expires_at is not None else None
            ),
            created_at=ApiTokenRepository._as_utc(row.created_at),
        )

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
