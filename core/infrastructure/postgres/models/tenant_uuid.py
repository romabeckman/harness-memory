import re
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

_SLUG_REGEX = re.compile(r"^[a-zA-Z0-9_-]+$")


class TenantUUID(UUID):
    """UUID subclass that compares equal to its valid string UUID representation or legacy slug."""

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, UUID):
            return super().__eq__(other)
        if isinstance(other, str):
            trimmed = other.strip()
            if not trimmed:
                return False
            try:
                return super().__eq__(UUID(trimmed))
            except ValueError:
                if _SLUG_REGEX.match(trimmed):
                    return super().__eq__(uuid5(NAMESPACE_DNS, trimmed))
                return False
        return False

    def __hash__(self) -> int:
        return super().__hash__()
