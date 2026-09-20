from datetime import UTC, datetime, timedelta


class TokenExpirationPolicy:
    maximum_lifetime = timedelta(days=90)

    def validate(
        self,
        expires_at: datetime,
        *,
        now: datetime | None = None,
        issued_at: datetime | None = None,
    ) -> datetime:
        current = now or datetime.now(UTC)
        normalized = self._as_utc(expires_at)
        current = self._as_utc(current)
        issuance = self._as_utc(issued_at or current)
        if normalized <= current or normalized > issuance + self.maximum_lifetime:
            raise ValueError("token expiration must be between 1 second and 90 days")
        return normalized

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
