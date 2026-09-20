from uuid import UUID

from pydantic import BaseModel


class ServiceAccountResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
