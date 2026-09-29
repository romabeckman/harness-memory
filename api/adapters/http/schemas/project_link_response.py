from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from api.adapters.http.schemas.linked_project_summary_schema import (
    LinkedProjectSummarySchema,
)


class ProjectLinkResponse(BaseModel):
    id: UUID
    linked_project: LinkedProjectSummarySchema
    created_at: datetime
    created_by: UUID | None = None
