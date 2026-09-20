from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.domain.entities.access_token import AccessToken
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken


class ApiTokenRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, token: AccessToken) -> AccessToken:
        with self._session_factory() as session:
            session.add(
                ApiAccessToken(
                    id=token.id,
                    user_id=token.user_id,
                    name=token.name,
                    token_hash=token.token_hash,
                    expires_at=token.expires_at,
                    created_at=token.created_at or datetime.now(UTC),
                )
            )
            session.commit()
        return token

    def get(self, token_id: UUID) -> AccessToken | None:
        with self._session_factory() as session:
            return self._to_domain(session.get(ApiAccessToken, token_id))

    def list(self, user_id: UUID | None = None) -> list[AccessToken]:
        statement = select(ApiAccessToken).order_by(ApiAccessToken.created_at)
        if user_id is not None:
            statement = statement.where(ApiAccessToken.user_id == user_id)
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

    @staticmethod
    def _to_domain(row: ApiAccessToken | None) -> AccessToken | None:
        if row is None:
            return None
        return AccessToken(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            token_hash=row.token_hash,
            expires_at=row.expires_at,
            created_at=row.created_at,
        )
