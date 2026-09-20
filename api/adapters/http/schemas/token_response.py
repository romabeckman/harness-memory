from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class TokenResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    expires_at: datetime
