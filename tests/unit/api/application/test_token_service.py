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
        project_keys=["catalog"],
        expires_at=now + timedelta(days=30),
        now=now,
    )

    assert issued.plaintext.startswith("hm_")
    assert issued.token.token_hash != issued.plaintext
    assert len(issued.token.token_hash) == 64
    assert issued.token.allowed_project_keys == frozenset({"catalog"})


def test_rejects_user_token_expiring_after_one_year():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    now = datetime(2026, 9, 20, tzinfo=UTC)

    with pytest.raises(ValueError, match="between 1 second and 365 days"):
        TokenService(Mock(), user_repository).create(
            user_id=user_id,
            name="automation",
            project_keys=["catalog"],
            expires_at=now + timedelta(days=366),
            now=now,
        )


def test_rejects_update_that_extends_user_token_beyond_original_one_year_window():
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
        allowed_project_keys=frozenset({"catalog"}),
    )

    with pytest.raises(ValueError, match="between 1 second and 365 days"):
        TokenService(token_repository, Mock()).update(
            token_repository.get.return_value.id,
            name=None,
            expires_at=issued_at + timedelta(days=366),
            now=now,
        )


def test_update_accepts_user_token_expiration_at_original_one_year_limit():
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
        allowed_project_keys=frozenset({"catalog"}),
    )
    token_repository.update.side_effect = lambda token: token

    updated = TokenService(token_repository, Mock()).update(
        token_repository.get.return_value.id,
        name=None,
        expires_at=issued_at + timedelta(days=365),
        now=now,
    )

    assert updated.expires_at == issued_at + timedelta(days=365)


def test_service_account_finite_lifetime_remains_limited_to_ninety_days():
    issued_at = datetime(2026, 9, 20, tzinfo=UTC)
    account = ServiceAccount(uuid4(), uuid4(), "Build agent")
    accounts = Mock()
    accounts.get.return_value = account
    service = TokenService(Mock(), Mock(), service_account_repository=accounts)

    with pytest.raises(ValueError, match="between 1 second and 90 days"):
        service.create(
            service_account_id=account.id,
            name="too-long",
            expires_at=issued_at + timedelta(days=91),
            now=issued_at,
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
    ).create(
        service_account_id=account.id,
        name="automation",
        project_keys=["catalog"],
        expires_at=None,
    )

    assert issued.token.user_id is None
    assert issued.token.service_account_id == account.id
    assert issued.token.expires_at is None
    assert issued.token.allowed_project_keys == frozenset({"catalog"})


def test_user_token_still_requires_expiration():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")

    with pytest.raises(ValueError, match="user tokens require an expiration"):
        TokenService(Mock(), user_repository).create(
            user_id=user_id,
            name="automation",
            project_keys=["catalog"],
            expires_at=None,
        )


def test_token_requires_exactly_one_owner():
    service = TokenService(Mock(), Mock(), service_account_repository=Mock())

    with pytest.raises(ValueError, match="exactly one token owner"):
        service.create(name="automation", project_keys=["catalog"], expires_at=None)


@pytest.mark.parametrize("project_keys", [[], None])
def test_create_empty_project_keys_grants_global_access(project_keys):
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    repository = Mock()
    repository.add.side_effect = lambda token: token
    service = TokenService(repository, user_repository)

    issued = service.create(
        user_id=user_id,
        name="automation",
        project_keys=project_keys,
        expires_at=datetime(2026, 10, 1, tzinfo=UTC),
    )
    assert issued.token.allowed_project_keys == frozenset({"*"})


def test_create_validates_projects_exist_globally():
    user_id = uuid4()
    tenant_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com", tenant_id=tenant_id)
    project_repo = Mock()
    project_repo.get_project_by_key.return_value = None
    service = TokenService(Mock(), user_repository, project_repository=project_repo)

    with pytest.raises(LookupError, match="project 'missing' not found"):
        service.create(
            user_id=user_id,
            name="automation",
            project_keys=["missing"],
            expires_at=datetime(2026, 10, 1, tzinfo=UTC),
        )


def test_user_token_accepts_one_year_and_rejects_longer_lifetime():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    token_repository = Mock()
    token_repository.add.side_effect = lambda token: token
    now = datetime(2026, 9, 20, tzinfo=UTC)
    service = TokenService(token_repository, user_repository)

    issued = service.create(
        user_id=user_id,
        name="annual",
        expires_at=now + timedelta(days=365),
        now=now,
    )

    assert issued.token.expires_at == now + timedelta(days=365)
    with pytest.raises(ValueError, match="between 1 second and 365 days"):
        service.create(
            user_id=user_id,
            name="too-long",
            expires_at=now + timedelta(days=366),
            now=now,
        )


def test_create_all_projects_skips_tenant_project_lookup():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com")
    project_repo = Mock()
    token_repository = Mock()
    token_repository.add.side_effect = lambda token: token

    issued = TokenService(
        token_repository, user_repository, project_repository=project_repo
    ).create(
        user_id=user_id,
        name="global-read",
        project_keys=["catalog", "*"],
        expires_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    assert issued.token.allowed_project_keys == frozenset({"*"})
    project_repo.get_project_by_key.assert_not_called()


def test_create_accepts_selected_project_from_another_tenant():
    user_id = uuid4()
    user_repository = Mock()
    user_repository.get.return_value = User(user_id, "Ada", "ada@example.com", tenant_id=uuid4())
    project_repository = Mock()
    project_repository.get_project_by_key.return_value = {
        "key": "cross-tenant-project",
        "tenant_id": str(uuid4()),
    }
    token_repository = Mock()
    token_repository.add.side_effect = lambda token: token

    issued = TokenService(
        token_repository, user_repository, project_repository=project_repository
    ).create(
        user_id=user_id,
        name="global-selection",
        project_keys=["cross-tenant-project"],
        expires_at=datetime(2026, 10, 1, tzinfo=UTC),
    )

    assert issued.token.allowed_project_keys == frozenset({"cross-tenant-project"})
    project_repository.get_project_by_key.assert_called_once_with("cross-tenant-project")
    project_repository.get_project.assert_not_called()
