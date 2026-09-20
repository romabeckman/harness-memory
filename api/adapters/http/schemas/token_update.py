from datetime import datetime

from pydantic import BaseModel, Field


class TokenUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    expires_at: datetime | None = None
