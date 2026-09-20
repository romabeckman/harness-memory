from unittest.mock import Mock
from uuid import uuid4

import pytest

from api.application.services.service_account_service import ServiceAccountService
from api.domain.entities.service_account import ServiceAccount


def test_creates_service_account_with_normalized_name_and_tenant():
    repository = Mock()
    repository.add.side_effect = lambda account: account
    tenant_id = uuid4()

    account = ServiceAccountService(repository).create(name="  Build agent  ", tenant_id=tenant_id)

    assert account.name == "Build agent"
    assert account.tenant_id == tenant_id
    repository.add.assert_called_once_with(account)


def test_lists_service_accounts_for_tenant():
    repository = Mock()
    tenant_id = uuid4()
    expected = [ServiceAccount(uuid4(), tenant_id, "Build agent")]
    repository.list.return_value = expected

    assert ServiceAccountService(repository).list(tenant_id) == expected
    repository.list.assert_called_once_with(tenant_id)


def test_updates_service_account_name():
    repository = Mock()
    account = ServiceAccount(uuid4(), uuid4(), "Build agent")
    repository.get.return_value = account
    repository.update.side_effect = lambda value: value

    updated = ServiceAccountService(repository).update(account.id, name=" Release bot ")

    assert updated.name == "Release bot"
    repository.update.assert_called_once_with(account)


def test_rejects_blank_service_account_name():
    repository = Mock()

    with pytest.raises(ValueError, match="name must not be empty"):
        ServiceAccountService(repository).create(name="  ", tenant_id=uuid4())


def test_get_raises_for_missing_service_account():
    repository = Mock()
    repository.get.return_value = None

    with pytest.raises(LookupError, match="service account not found"):
        ServiceAccountService(repository).get(uuid4())
