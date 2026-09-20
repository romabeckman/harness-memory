from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FoundationId(BaseModel):
    value: UUID

    model_config = ConfigDict(frozen=True)
