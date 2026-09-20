from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest

from api.application.services.token_service import TokenService
from api.domain.entities.access_token import AccessToken
from api.domain.entities.service_account import ServiceAccount
from api.domain.entities.user import User


def test_issues_hashed_token_with_plaintext_returned_once():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    token_repository = Mock()
    token_repository.add.side_effect = lambda token: token
    now = datetime(2026, 9, 20, tzinfo=UTC)

    issued = TokenService(token_repository, user_repository).create(
        user_id=user_id,
        name="automation",
        expires_at=now + timedelta(days=30),
        now=now,
    )

    assert issued.plaintext.startswith("hm_")
    assert issued.token.token_hash != issued.plaintext
    assert len(issued.token.token_hash) == 64


def test_rejects_token_expiring_after_ninety_days():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    now = datetime(2026, 9, 20, tzinfo=UTC)

    with pytest.raises(ValueError, match="between 1 second and 90 days"):
        TokenService(Mock(), user_repository).create(
            user_id=user_id,
            name="automation",
            expires_at=now + timedelta(days=91),
            now=now,
        )


def test_rejects_update_that_extends_token_beyond_original_ninety_day_window():
    issued_at = datetime(2026, 8, 1, tzinfo=UTC)
    now = datetime(2026, 9, 20, tzinfo=UTC)
    token_repository = Mock()
    token_repository.get.return_value = AccessToken(
        id=uuid4(),
        user_id=uuid4(),
        name="automation",
        token_hash="a" * 64,
        expires_at=issued_at + timedelta(days=60),
        created_at=issued_at,
    )

    with pytest.raises(ValueError, match="between 1 second and 90 days"):
        TokenService(token_repository, Mock()).update(
            token_repository.get.return_value.id,
            name=None,
            expires_at=issued_at + timedelta(days=91),
            now=now,
        )


def test_issues_non_expiring_token_for_service_account():
    tenant_id = uuid4()
    account = ServiceAccount(uuid4(), tenant_id, "Build agent")
    service_account_repository = Mock()
    service_account_repository.get.return_value = account
    token_repository = Mock()
    token_repository.add.side_effect = lambda token: token

    issued = TokenService(
        token_repository,
        Mock(),
        service_account_repository=service_account_repository,
    ).create(service_account_id=account.id, name="automation", expires_at=None)

    assert issued.token.user_id is None
    assert issued.token.service_account_id == account.id
    assert issued.token.expires_at is None


def test_user_token_still_requires_expiration():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")

    with pytest.raises(ValueError, match="user tokens require an expiration"):
        TokenService(Mock(), user_repository).create(
            user_id=user_id, name="automation", expires_at=None
        )


def test_token_requires_exactly_one_owner():
    service = TokenService(Mock(), Mock(), service_account_repository=Mock())

    with pytest.raises(ValueError, match="exactly one token owner"):
        service.create(name="automation", expires_at=None)
