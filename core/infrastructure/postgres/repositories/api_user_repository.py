from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from api.domain.entities.user import User
from core.infrastructure.postgres.models.api_user import ApiUser


class ApiUserRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def add(self, user: User) -> User:
        with self._session_factory() as session:
            session.add(ApiUser(id=user.id, name=user.name, email=user.email))
            session.commit()
        return user

    def get(self, user_id: UUID) -> User | None:
        with self._session_factory() as session:
            return self._to_domain(session.get(ApiUser, user_id))

    def find_by_email(self, email: str) -> User | None:
        with self._session_factory() as session:
            return self._to_domain(session.scalar(select(ApiUser).where(ApiUser.email == email)))

    def list(self) -> list[User]:
        with self._session_factory() as session:
            rows = session.scalars(select(ApiUser).order_by(ApiUser.email)).all()
            return [User(id=row.id, name=row.name, email=row.email) for row in rows]

    def update(self, user: User) -> User:
        with self._session_factory() as session:
            row = session.get(ApiUser, user.id)
            if row is None:
                raise LookupError("user not found")
            row.name = user.name
            row.email = user.email
            session.commit()
        return user

    def delete(self, user_id: UUID) -> None:
        with self._session_factory() as session:
            row = session.get(ApiUser, user_id)
            if row is not None:
                session.delete(row)
                session.commit()

    @staticmethod
    def _to_domain(row: ApiUser | None) -> User | None:
        if row is None:
            return None
        return User(id=row.id, name=row.name, email=row.email)
