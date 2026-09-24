from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr
from uuid import UUID


class ProjectSearchItem(BaseModel):
    key: StrictStr = Field(min_length=1, max_length=255)
    tenant_id: str | None = None
    tenant_key: str | None = None
    project_id: UUID | None = None
    active_snapshot_id: UUID | None = None
    environment_names: tuple[str, ...] | None = None
    name: StrictStr | None = Field(default=None, max_length=255)
    has_active_snapshot: StrictBool

    model_config = ConfigDict(frozen=True, extra="forbid")
