from typing import Any
from pydantic import BaseModel, Field


class KnowledgePublicationRequest(BaseModel):
    project_key: str = Field(..., min_length=1)
    environment: str = Field(..., min_length=1)
    deployment_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    entities: list[Any] = Field(default_factory=list)
    relations: list[Any] = Field(default_factory=list)
    evidence: list[Any] = Field(default_factory=list)
