from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr

from .project_environment_item import ProjectEnvironmentItem


class ProjectSearchItem(BaseModel):
    key: StrictStr = Field(min_length=1, max_length=255)
    tenant_id: str | None = None
    tenant_key: str | None = None
    project_id: UUID | None = None
    environments: tuple[ProjectEnvironmentItem, ...] = ()
    name: StrictStr | None = Field(default=None, max_length=255)
    has_active_snapshot: StrictBool

    model_config = ConfigDict(frozen=True, extra="forbid")
