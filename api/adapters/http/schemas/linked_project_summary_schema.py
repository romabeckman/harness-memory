from uuid import UUID

from pydantic import BaseModel


class LinkedProjectSummarySchema(BaseModel):
    project_id: UUID
    key: str
    name: str | None = None
    tenant_id: UUID
