from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class ProjectInput(BaseModel):
    key: str = Field(min_length=1, max_length=255)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "name")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return trim_bounded(value, "project field", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
