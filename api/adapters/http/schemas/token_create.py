from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TokenCreate(BaseModel):
    user_id: UUID | None = None
    service_account_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None
    scopes: set[str] = Field(default_factory=lambda: {"memory:read"}, min_length=1)

    @model_validator(mode="after")
    def require_one_owner(self):
        if (self.user_id is None) == (self.service_account_id is None):
            raise ValueError("exactly one token owner is required")
        return self
