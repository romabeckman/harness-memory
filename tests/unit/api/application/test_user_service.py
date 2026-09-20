from unittest.mock import Mock
from uuid import uuid4

import pytest

from api.application.services.user_service import UserService
from api.domain.entities.user import User


def test_creates_normalized_user():
    repository = Mock()
    repository.find_by_email.return_value = None
    repository.add.side_effect = lambda user: user

    user = UserService(repository).create("  Ada  ", " ADA@EXAMPLE.COM ")

    assert user.name == "Ada"
    assert user.email == "ada@example.com"
    repository.add.assert_called_once_with(user)


def test_rejects_duplicate_user_email():
    repository = Mock()
    repository.find_by_email.return_value = User(uuid4(), "Ada", "ada@example.com")

    with pytest.raises(ValueError, match="email already exists"):
        UserService(repository).create("Other", "ada@example.com")
