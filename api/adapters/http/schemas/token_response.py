from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenResponse(BaseModel):
    id: UUID
    user_id: UUID | None
    service_account_id: UUID | None
    name: str
    expires_at: datetime | None
