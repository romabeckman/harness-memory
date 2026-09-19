from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .base import trim_bounded, validate_metadata


class EvidenceInput(BaseModel):
    source: str = Field(min_length=1, max_length=1024)
    excerpt: str | None = Field(default=None, max_length=4096)
    relation_ref: str | None = Field(default=None, min_length=1, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("source")
    @classmethod
    def trim_source(cls, value: str) -> str:
        return trim_bounded(value, "evidence source", 1024)

    @field_validator("excerpt")
    @classmethod
    def trim_excerpt(cls, value: str | None) -> str | None:
        return trim_bounded(value, "evidence excerpt", 4096)

    @field_validator("relation_ref")
    @classmethod
    def trim_relation_reference(cls, value: str | None) -> str | None:
        return trim_bounded(value, "evidence relation reference", 255)

    @field_validator("metadata")
    @classmethod
    def metadata_is_bounded_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        return validate_metadata(value)
