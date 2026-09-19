from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictStr


class EvidenceView(BaseModel):
    id: UUID
    source: StrictStr = Field(min_length=1, max_length=1024)
    excerpt: StrictStr | None = Field(default=None, max_length=4096)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")
