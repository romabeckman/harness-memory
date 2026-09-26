from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TokenCreate(BaseModel):
    user_id: UUID | None = None
    service_account_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = None
    scopes: set[str] = Field(default_factory=lambda: {"memory:read"}, min_length=1)
    project_keys: list[str] = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_token_create(self):
        if (self.user_id is None) == (self.service_account_id is None):
            raise ValueError("exactly one token owner is required")
        cleaned_projects = [k.strip() for k in self.project_keys if isinstance(k, str) and k.strip()]
        if not cleaned_projects:
            raise ValueError("at least one project key is required")
        self.project_keys = list(dict.fromkeys(cleaned_projects))
        return self
