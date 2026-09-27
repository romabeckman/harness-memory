from datetime import datetime

from pydantic import BaseModel, Field


class TokenUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    expires_at: datetime | None = Field(
        default=None,
        description="Maximum 365 days from issuance for user tokens; maximum 90 days for expiring service-account tokens.",
    )
