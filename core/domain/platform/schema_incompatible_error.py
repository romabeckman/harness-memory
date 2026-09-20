import re


class SchemaIncompatibleError(Exception):
    """Raised when the database schema revision does not match the expected head revision."""

    def __init__(
        self,
        current_revision: str | None,
        head_revision: str,
        message: str | None = None,
    ):
        mismatch = f"Database revision '{current_revision}' does not match head '{head_revision}'"
        raw_message = f"{mismatch}: {message}" if message else mismatch
        sanitized_msg = self._sanitize_message(raw_message)
        super().__init__(sanitized_msg)
        self.current_revision = current_revision
        self.head_revision = head_revision

    @staticmethod
    def _sanitize_message(message: str) -> str:
        sanitized = re.sub(
            r"(?i)postgres(?:ql)?(?:\+[^:/\s]+)?://[^\s,;]+",
            "<redacted-database-url>",
            message,
        )
        sanitized = re.sub(
            r"(?i)(password|token|secret|authorization|database_url)\s*[=:]\s*[^\s,;]+",
            "<redacted>",
            sanitized,
        )
        return sanitized[:512]
