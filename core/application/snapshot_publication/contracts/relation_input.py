from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class RelationInput(BaseModel):
    ref: str = Field(
        min_length=1,
        max_length=255,
        description="Snapshot-local relation reference used to attach supporting evidence.",
    )
    source_entity_key: str = Field(
        min_length=1,
        max_length=255,
        description="Key of the entity where this relationship starts.",
    )
    type: Literal[
        "part_of",
        "owned_by",
        "provides",
        "consumes",
        "depends_on",
        "publishes",
        "subscribes_to",
        "implements",
    ] = Field(
        description="Relationship type that defines how the source entity relates to the target."
    )
    target_entity_key: str = Field(
        min_length=1,
        max_length=255,
        description="Key of the entity where this relationship ends.",
    )
    provenance: Literal["declared", "inferred", "observed", "manual"] = Field(
        description=(
            "How this relationship was established: declared, inferred, observed, or manual."
        )
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional bounded JSON metadata for the relationship.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("ref", "source_entity_key", "target_entity_key")
    @classmethod
    def trim_key(cls, value: str) -> str:
        return trim_bounded(value, "relation field", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
