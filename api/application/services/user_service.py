from uuid import UUID, uuid4

from api.application.ports.user_repository import UserRepository
from api.domain.entities.user import User


class UserService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def create(self, name: str, email: str) -> User:
        normalized_name = self._normalize_name(name)
        normalized_email = self._normalize_email(email)
        if self._repository.find_by_email(normalized_email) is not None:
            raise ValueError("email already exists")
        return self._repository.add(User(uuid4(), normalized_name, normalized_email))

    def get(self, user_id: UUID) -> User:
        user = self._repository.get(user_id)
        if user is None:
            raise LookupError("user not found")
        return user

    def list(
        self,
        *,
        name: str | None = None,
        email: str | None = None,
        q: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        return self._repository.list(name=name, email=email, q=q, limit=limit, offset=offset)

    def update(self, user_id: UUID, *, name: str | None, email: str | None) -> User:
        user = self.get(user_id)
        if name is not None:
            user.name = self._normalize_name(name)
        if email is not None:
            normalized_email = self._normalize_email(email)
            owner = self._repository.find_by_email(normalized_email)
            if owner is not None and owner.id != user_id:
                raise ValueError("email already exists")
            user.email = normalized_email
        return self._repository.update(user)

    def delete(self, user_id: UUID) -> None:
        self.get(user_id)
        self._repository.delete(user_id)

    @staticmethod
    def _normalize_name(name: str) -> str:
        value = name.strip()
        if not value:
            raise ValueError("name must not be empty")
        return value

    @staticmethod
    def _normalize_email(email: str) -> str:
        value = email.strip().lower()
        if not value or "@" not in value:
            raise ValueError("email must be valid")
        return value
