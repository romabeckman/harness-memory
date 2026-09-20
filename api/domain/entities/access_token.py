from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(slots=True)
class AccessToken:
    id: UUID
    user_id: UUID
    name: str
    token_hash: str
    expires_at: datetime
    created_at: datetime | None = None
