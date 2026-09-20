from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from core.domain.snapshot_publication.types.entity_type import EntityType


class EntitySearchItem(BaseModel):
    entity_id: UUID
    key: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    type: EntityType
    project_key: str = Field(min_length=1, max_length=255)
    project_name: str | None = Field(default=None, min_length=1, max_length=255)
    snapshot_id: UUID
    revision: StrictInt = Field(ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")
