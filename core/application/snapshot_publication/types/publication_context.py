from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True, slots=True)
class PublicationContext:
    tenant_id: str
    scopes: FrozenSet[str] | None = None
    is_admin: bool = False

    def __post_init__(self) -> None:
        value = self.tenant_id.strip() if isinstance(self.tenant_id, str) else ""
        if not value:
            raise ValueError("tenant context is required")
        object.__setattr__(self, "tenant_id", value)
        if self.scopes is not None:
            object.__setattr__(self, "scopes", frozenset(self.scopes))
