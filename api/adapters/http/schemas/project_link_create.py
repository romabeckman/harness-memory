from uuid import UUID

from pydantic import BaseModel, Field


class ProjectLinkCreateRequest(BaseModel):
    target_project_key: str = Field(min_length=1)
    target_tenant_id: UUID | None = None
    created_by: UUID | None = None
