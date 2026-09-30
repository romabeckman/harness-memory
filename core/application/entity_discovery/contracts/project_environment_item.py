from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ProjectEnvironmentItem(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=64)
    current_snapshot_id: UUID | None = None
    environment_type: StrictStr | None = None
    entity_count: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(frozen=True, extra="forbid")
