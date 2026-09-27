from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.domain.entities.access_token import AccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User
from core.infrastructure.postgres.models.api_access_token import ApiAccessToken
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.api_service_account_repository import (
    ApiServiceAccountRepository,
)
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository


def test_user_and_token_repositories_persist_crud():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
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
        allowed_project_keys=frozenset({"proj-1"}),
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


def test_user_deletion_cascades_all_owned_tokens():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    users = ApiUserRepository(factory)
    tokens = ApiTokenRepository(factory)
    user = users.add(User(uuid4(), "Ada", "ada@example.com"))
    owned_tokens = [
        AccessToken(
            id=uuid4(),
            user_id=user.id,
            name=f"automation-{index}",
            token_hash=str(index) * 64,
            expires_at=datetime.now(UTC) + timedelta(days=30),
            allowed_project_keys=frozenset({"proj-1"}),
        )
        for index in (1, 2)
    ]
    for token in owned_tokens:
        tokens.add(token)

    users.delete(user.id)

    assert users.get(user.id) is None
    assert all(tokens.get(token.id) is None for token in owned_tokens)


def test_token_repository_authenticates_only_unexpired_hashes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    users = ApiUserRepository(factory)
    tokens = ApiTokenRepository(factory)
    user = users.add(User(uuid4(), "Ada", "ada@example.com"))
    now = datetime.now(UTC)
    active = AccessToken(
        uuid4(),
        user.id,
        "active",
        "a" * 64,
        now + timedelta(days=1),
        now,
        allowed_project_keys=frozenset({"proj-1"}),
    )
    expired = AccessToken(
        uuid4(),
        user.id,
        "expired",
        "b" * 64,
        now - timedelta(days=1),
        now,
        allowed_project_keys=frozenset({"proj-1"}),
    )
    tokens.add(active)
    tokens.add(expired)

    authenticated = tokens.find_active_by_hash("a" * 64, now=now)

    assert authenticated == (active, user)
    assert tokens.find_active_by_hash("b" * 64, now=now) is None


def test_service_account_repository_and_non_expiring_token():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(
        engine,
        tables=[ApiUser.__table__, ApiServiceAccount.__table__, ApiAccessToken.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    accounts = ApiServiceAccountRepository(factory)
    tokens = ApiTokenRepository(factory)
    account = accounts.add(ServiceAccount(uuid4(), uuid4(), "Build agent"))
    now = datetime.now(UTC)
    token = AccessToken(
        id=uuid4(),
        user_id=None,
        name="automation",
        token_hash="c" * 64,
        expires_at=None,
        created_at=now,
        service_account_id=account.id,
        allowed_project_keys=frozenset({"proj-1"}),
    )

    tokens.add(token)

    assert accounts.get(account.id) == account
    assert accounts.list(account.tenant_id) == [account]
    assert tokens.find_active_by_hash(token.token_hash, now=now) == (token, account)

    accounts.delete(account.id)

    assert tokens.get(token.id) is None


def test_service_account_repository_filters_and_pages_in_database():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[ApiServiceAccount.__table__])
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    accounts = ApiServiceAccountRepository(factory)
    tenant_id = uuid4()
    for index in range(25):
        accounts.add(ServiceAccount(uuid4(), tenant_id, f"Release agent {index:02d}"))

    statements = []
    from sqlalchemy import event

    @event.listens_for(engine, "before_cursor_execute")
    def record_query(connection, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith("SELECT") and "FROM service_accounts" in statement:
            statements.append(statement.upper())

    result = accounts.list(tenant_id=tenant_id, q="RELEASE", limit=5, offset=20)

    assert [account.name for account in result] == [
        f"Release agent {index:02d}" for index in range(20, 25)
    ]
    assert len(statements) == 1
    assert "LIMIT" in statements[0] and "OFFSET" in statements[0] and "LIKE" in statements[0]
