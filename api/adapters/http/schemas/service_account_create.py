from uuid import UUID

from pydantic import BaseModel, Field


class ServiceAccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    tenant_id: UUID
