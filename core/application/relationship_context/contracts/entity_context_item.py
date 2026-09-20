from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr

from core.domain.snapshot_publication.types.entity_type import EntityType


class EntityContextItem(BaseModel):
    id: UUID
    identity_id: UUID | None = Field(default=None, exclude=True)
    key: StrictStr = Field(min_length=1, max_length=255)
    name: StrictStr | None = Field(default=None, max_length=255)
    type: EntityType
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")
