from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.domain.entities.access_token import AccessToken
from api.domain.entities.user import User
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository


def test_user_and_token_repositories_persist_crud():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[ApiUser.__table__, ApiAccessToken.__table__])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    users = ApiUserRepository(factory)
    tokens = ApiTokenRepository(factory)
    user = users.add(User(uuid4(), "Ada", "ada@example.com"))
    token = AccessToken(
        id=uuid4(),
        user_id=user.id,
        name="automation",
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )

    tokens.add(token)
    token.name = "renamed"
    tokens.update(token)

    assert users.get(user.id) == user
    assert tokens.get(token.id).name == "renamed"
    tokens.delete(token.id)
    users.delete(user.id)
    assert tokens.get(token.id) is None
    assert users.get(user.id) is None
