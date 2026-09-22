from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class AccessToken:
    id: UUID
    user_id: UUID | None
    name: str
    token_hash: str
    expires_at: datetime | None
    created_at: datetime | None = None
    service_account_id: UUID | None = None
    scopes: frozenset[str] = field(default_factory=lambda: frozenset({"memory:read"}))

    def __post_init__(self) -> None:
        if (self.user_id is None) == (self.service_account_id is None):
            raise ValueError("exactly one token owner is required")
        if not self.scopes:
            raise ValueError("at least one scope is required")
