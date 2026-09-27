from typing import Protocol
from uuid import UUID

from api.domain.entities.user import User


class UserRepository(Protocol):
    def add(self, user: User) -> User: ...

    def get(self, user_id: UUID) -> User | None: ...

    def find_by_email(self, email: str) -> User | None: ...

    def list(
        self, *, name: str | None = None, email: str | None = None,
        q: str | None = None, limit: int = 100, offset: int = 0,
    ) -> list[User]: ...

    def update(self, user: User) -> User: ...

    def delete(self, user_id: UUID) -> None: ...
