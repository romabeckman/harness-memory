from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class EntityInput(BaseModel):
    key: str = Field(
        min_length=1,
        max_length=255,
        description="Stable key used to identify this entity in relations and searches.",
    )
    type: Literal["project", "system", "service", "api", "event", "library", "team"] = Field(
        description="Entity category in the corporate knowledge graph."
    )
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Human-readable entity name.",
    )
    canonical_key: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Optional normalized key used to match equivalent entity identifiers.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional bounded JSON metadata for the entity.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "name", "canonical_key")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return trim_bounded(value, "entity field", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
