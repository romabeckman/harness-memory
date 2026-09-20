from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class ProjectContextItem(BaseModel):
    key: StrictStr = Field(min_length=1, max_length=255)
    name: StrictStr | None = Field(default=None, max_length=255)
    snapshot_id: UUID
    revision: StrictInt = Field(ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")
