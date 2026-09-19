from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from core.domain.snapshot_publication.types.entity_type import EntityType


class EntitySearchItem(BaseModel):
    entity_id: UUID
    key: str
    name: str | None = None
    type: EntityType
    project_key: str
    project_name: str | None = None
    snapshot_id: UUID
    revision: StrictInt = Field(ge=1)

    model_config = ConfigDict(frozen=True, extra="forbid")
