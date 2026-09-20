from typing import Any


class TelemetrySpanSanitizer:
    """Sanitizes telemetry span attributes by stripping secrets and truncating oversized strings."""

    _SENSITIVE_KEYS = frozenset(
        {
            "authorization",
            "token",
            "password",
            "payload",
            "database_url",
            "secret",
            "credentials",
            "api_key",
        }
    )
    _MAX_STRING_LENGTH = 256

    @classmethod
    def sanitize(cls, attributes: dict[str, Any] | None) -> dict[str, Any]:
        if not attributes:
            return {}

        sanitized: dict[str, Any] = {}
        for key, value in attributes.items():
            if not isinstance(key, str):
                continue
            normalized_key = key.strip().lower()
            if normalized_key in cls._SENSITIVE_KEYS or any(
                sensitive in normalized_key
                for sensitive in (
                    "password",
                    "secret",
                    "token",
                    "database_url",
                    "payload",
                    "authorization",
                    "bearer",
                    "jwt",
                    "claim",
                    "evidence",
                )
            ):
                continue

            if isinstance(value, str):
                if len(value) > cls._MAX_STRING_LENGTH:
                    sanitized[key] = value[: cls._MAX_STRING_LENGTH - 3] + "..."
                else:
                    sanitized[key] = value
            elif isinstance(value, (int, float, bool)):
                sanitized[key] = value
            elif value is None:
                continue
            else:
                # Omit non-primitive or complex structures to avoid leaking internal state
                continue

        return sanitized
