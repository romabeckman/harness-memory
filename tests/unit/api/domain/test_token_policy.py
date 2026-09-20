from datetime import UTC, datetime, timedelta

import pytest

from api.domain.services.token_expiration_policy import TokenExpirationPolicy


def test_accepts_expiration_at_ninety_day_limit():
    now = datetime(2026, 9, 20, tzinfo=UTC)

    expiration = TokenExpirationPolicy().validate(now + timedelta(days=90), now=now)

    assert expiration == now + timedelta(days=90)


@pytest.mark.parametrize("days", [0, 91])
def test_rejects_expiration_outside_allowed_window(days):
    now = datetime(2026, 9, 20, tzinfo=UTC)

    with pytest.raises(ValueError, match="between 1 second and 90 days"):
        TokenExpirationPolicy().validate(now + timedelta(days=days), now=now)
