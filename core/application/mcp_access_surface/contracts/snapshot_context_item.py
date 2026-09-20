from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class SnapshotContextItem(BaseModel):
    id: UUID
    project_key: StrictStr = Field(min_length=1, max_length=255)
    revision: StrictInt = Field(ge=1)
    schema_version: StrictStr = Field(min_length=1, max_length=64)
    payload_hash: StrictStr | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")
