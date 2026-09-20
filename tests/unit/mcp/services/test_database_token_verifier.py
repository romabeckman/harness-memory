import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

from api.domain.entities.access_token import AccessToken as DomainAccessToken
from api.domain.entities.user import User
from mcp.services.database_token_verifier import DatabaseTokenVerifier


def test_database_token_verifier_maps_active_api_token_to_mcp_identity():
    user = User(uuid4(), "Ada", "ada@example.com")
    stored = DomainAccessToken(
        id=uuid4(),
        user_id=user.id,
        name="client",
        token_hash="a" * 64,
        expires_at=datetime.now(UTC) + timedelta(days=1),
    )
    repository = Mock()
    repository.find_active_by_hash.return_value = (stored, user)

    verified = asyncio.run(DatabaseTokenVerifier(repository).verify_token("hm_secret"))

    assert verified.subject == str(user.id)
    assert verified.claims["tenant_id"] == str(user.id)
    assert set(verified.scopes) == {"memory:read", "memory:publish", "memory:impact"}
    repository.find_active_by_hash.assert_called_once()


def test_database_token_verifier_rejects_unknown_token():
    repository = Mock()
    repository.find_active_by_hash.return_value = None

    assert asyncio.run(DatabaseTokenVerifier(repository).verify_token("unknown")) is None
