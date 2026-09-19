from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ChangeDescription(BaseModel):
    entity_id: UUID
    change_type: StrictStr = Field(default="contract", min_length=1, max_length=64)
    description: StrictStr = Field(default="", max_length=4096)
    changed_fields: tuple[StrictStr, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")
