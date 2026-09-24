from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class KnowledgePublicationRequest(BaseModel):
    tenant_id: UUID | None = None
    project_key: str = Field(..., min_length=1)
    environment: str = Field(..., min_length=1)
    deployment_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    expected_current_snapshot_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    entities: list[Any] = Field(default_factory=list)
    relations: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
