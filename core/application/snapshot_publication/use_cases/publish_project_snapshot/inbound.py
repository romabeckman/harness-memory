from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from ...contracts.base import normalize_datetime
from ...contracts.entity_input import EntityInput
from ...contracts.evidence_input import EvidenceInput
from ...contracts.project_input import ProjectInput
from ...contracts.relation_input import RelationInput


class PublishProjectSnapshotInput(BaseModel):
    schema_version: Literal["1.0"]
    project: ProjectInput
    revision: StrictInt = Field(ge=1)
    generated_at: datetime
    entities: tuple[EntityInput, ...] = Field(default_factory=tuple, max_length=10_000)
    relations: tuple[RelationInput, ...] = Field(default_factory=tuple, max_length=50_000)
    evidence: tuple[EvidenceInput, ...] = Field(default_factory=tuple, max_length=50_000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("generated_at")
    @classmethod
    def generated_at_is_offset_aware_utc(cls, value: datetime) -> datetime:
        return normalize_datetime(value)

    @model_validator(mode="after")
    def canonical_payload_is_bounded(self):
        payload = self.model_dump(mode="json")
        import json

        encoded = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        if len(encoded) > 10 * 1024 * 1024:
            raise ValueError("canonical snapshot payload exceeds 10 MiB")
        return self
