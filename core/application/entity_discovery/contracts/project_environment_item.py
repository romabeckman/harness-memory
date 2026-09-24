from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ProjectEnvironmentItem(BaseModel):
    name: StrictStr = Field(min_length=1, max_length=64)
    current_snapshot_id: UUID | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")
