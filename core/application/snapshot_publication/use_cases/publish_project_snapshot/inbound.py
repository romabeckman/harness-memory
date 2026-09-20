from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

from ...contracts.base import normalize_datetime
from ...contracts.entity_input import EntityInput
from ...contracts.evidence_input import EvidenceInput
from ...contracts.project_input import ProjectInput
from ...contracts.relation_input import RelationInput


class PublishProjectSnapshotInput(BaseModel):
    schema_version: Literal["1.0"] = Field(
        description="Snapshot payload schema version; currently 1.0."
    )
    project: ProjectInput = Field(
        description="Project identity and metadata for this snapshot."
    )
    revision: StrictInt = Field(
        ge=1,
        description="Positive revision used to order and deduplicate project snapshots.",
    )
    generated_at: datetime = Field(
        description="Snapshot generation timestamp with an explicit UTC offset."
    )
    entities: tuple[EntityInput, ...] = Field(
        default_factory=tuple,
        max_length=10_000,
        description="Entities owned by this project snapshot.",
    )
    relations: tuple[RelationInput, ...] = Field(
        default_factory=tuple,
        max_length=50_000,
        description="Relationships between entities, with provenance and optional metadata.",
    )
    evidence: tuple[EvidenceInput, ...] = Field(
        default_factory=tuple,
        max_length=50_000,
        description="Source records that support snapshot facts or relation references.",
    )

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
