import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

from api.domain.entities.access_token import AccessToken as DomainAccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User
from harness_memory_mcp.services.database_token_verifier import DatabaseTokenVerifier


def test_admin_token_is_global_and_keeps_all_mcp_scopes():
    repository = Mock()
    verified = asyncio.run(
        DatabaseTokenVerifier(repository, admin_token="admin-secret").verify_token(
            "admin-secret"
        )
    )
    assert verified.claims["tenant_id"] == "*"
    assert verified.claims["is_admin"] is True
    assert set(verified.scopes) == {"memory:read", "memory:impact", "memory:publish"}
    repository.find_active_by_hash.assert_not_called()


def test_read_api_key_is_global_and_has_only_memory_read_scope():
    repository = Mock()
    verified = asyncio.run(
        DatabaseTokenVerifier(repository, read_api_key="read-secret").verify_token(
            "read-secret"
        )
    )

    assert verified.claims["tenant_id"] == "*"
    assert verified.claims["is_admin"] is True
    assert set(verified.scopes) == {"memory:read"}
    repository.find_active_by_hash.assert_not_called()


def test_database_token_verifier_maps_active_api_token_to_mcp_identity():
    user = User(uuid4(), "Ada", "ada@example.com")
    stored = DomainAccessToken(
        id=uuid4(),
        user_id=user.id,
        name="client",
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        scopes=frozenset({"memory:read"}),
    )
    repository = Mock()
    repository.find_active_by_hash.return_value = (stored, user)

    verified = asyncio.run(DatabaseTokenVerifier(repository).verify_token("hm_secret"))

    assert verified.subject == str(user.id)
    assert verified.claims["tenant_id"] == str(user.id)
    assert set(verified.scopes) == {"memory:read"}
    repository.find_active_by_hash.assert_called_once()


def test_database_token_verifier_rejects_unknown_token():
    repository = Mock()
    repository.find_active_by_hash.return_value = None

    assert asyncio.run(DatabaseTokenVerifier(repository).verify_token("unknown")) is None


def test_database_token_verifier_rejects_blank_token_before_lookup():
    repository = Mock()

    assert asyncio.run(DatabaseTokenVerifier(repository).verify_token("   ")) is None

    repository.find_active_by_hash.assert_not_called()


def test_database_token_verifier_rejects_ownerless_active_token():
    stored = DomainAccessToken(
        id=uuid4(),
        user_id=uuid4(),
        name="client",
        token_hash="c" * 64,
        expires_at=None,
        scopes=frozenset({"memory:read"}),
    )
    repository = Mock()
    repository.find_active_by_hash.return_value = (stored, None)

    assert asyncio.run(DatabaseTokenVerifier(repository).verify_token("ownerless")) is None


def test_database_token_verifier_uses_service_account_tenant_and_allows_no_expiry():
    account = ServiceAccount(uuid4(), uuid4(), "deployment agent")
    stored = DomainAccessToken(
        id=uuid4(),
        user_id=None,
        name="client",
        token_hash="b" * 64,
        expires_at=None,
        service_account_id=account.id,
        scopes=frozenset({"memory:publish"}),
    )
    repository = Mock()
    repository.find_active_by_hash.return_value = (stored, account)

    verified = asyncio.run(DatabaseTokenVerifier(repository).verify_token("hm_secret"))

    assert verified.subject == str(account.id)
    assert verified.claims["tenant_id"] == str(account.tenant_id)
    assert verified.expires_at is None
    assert set(verified.scopes) == {"memory:publish"}
