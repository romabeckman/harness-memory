from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class EntityInput(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    type: Literal["project", "system", "service", "api", "event", "library", "team"]
    name: str | None = Field(default=None, min_length=1, max_length=255)
    canonical_key: str | None = Field(default=None, min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "name", "canonical_key")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return trim_bounded(value, "entity field", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
