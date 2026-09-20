from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TokenCreate(BaseModel):
    user_id: UUID
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime
