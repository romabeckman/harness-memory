from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

ProjectText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: UUID
    key: ProjectText
    name: ProjectText | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
