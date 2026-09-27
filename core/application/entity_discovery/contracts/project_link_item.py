from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ProjectLinkItem(BaseModel):
    project_id: UUID
    name: StrictStr | None = Field(default=None, max_length=255)
    tenant_id: UUID | str

    model_config = ConfigDict(frozen=True, extra="forbid")
