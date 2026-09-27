from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class TokenCreate(BaseModel):
    user_id: UUID | None = None
    service_account_id: UUID | None = None
    name: str = Field(min_length=1, max_length=120)
    expires_at: datetime | None = Field(
        default=None,
        description="Required for user tokens. Maximum 365 days from issuance for users; maximum 90 days for expiring service-account tokens.",
    )
    scopes: set[str] = Field(default_factory=lambda: {"memory:read"}, min_length=1)
    project_keys: list[str] | None = Field(
        default=None,
        description="Empty, null, or omitted grants all projects across all tenants. An owner is still required; tenant_id is not a token scope field.",
    )

    @model_validator(mode="after")
    def validate_token_create(self):
        if (self.user_id is None) == (self.service_account_id is None):
            raise ValueError("exactly one token owner is required")
        cleaned_projects = [k.strip() for k in (self.project_keys or []) if isinstance(k, str) and k.strip()]
        if self.project_keys and not cleaned_projects:
            raise ValueError("at least one project key is required")
        self.project_keys = list(dict.fromkeys(cleaned_projects))
        return self
