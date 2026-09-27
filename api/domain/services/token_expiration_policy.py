from datetime import UTC, datetime, timedelta


class TokenExpirationPolicy:
    maximum_lifetime = timedelta(days=90)
    user_maximum_lifetime = timedelta(days=365)

    def validate(
        self,
        expires_at: datetime,
        *,
        now: datetime | None = None,
        issued_at: datetime | None = None,
        user_owned: bool = False,
    ) -> datetime:
        current = now or datetime.now(UTC)
        normalized = self._as_utc(expires_at)
        current = self._as_utc(current)
        issuance = self._as_utc(issued_at or current)
        maximum_lifetime = self.user_maximum_lifetime if user_owned else self.maximum_lifetime
        if normalized <= current or normalized > issuance + maximum_lifetime:
            raise ValueError(
                f"token expiration must be between 1 second and {maximum_lifetime.days} days"
            )
        return normalized

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
