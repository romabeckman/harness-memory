from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class RelationInput(BaseModel):
    ref: str = Field(min_length=1, max_length=255)
    source_entity_key: str = Field(min_length=1, max_length=255)
    type: Literal[
        "part_of",
        "owned_by",
        "provides",
        "consumes",
        "depends_on",
        "publishes",
        "subscribes_to",
        "implements",
    ]
    target_entity_key: str = Field(min_length=1, max_length=255)
    provenance: Literal["declared", "inferred", "observed", "manual"]
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("ref", "source_entity_key", "target_entity_key")
    @classmethod
    def trim_key(cls, value: str) -> str:
        return trim_bounded(value, "relation field", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
