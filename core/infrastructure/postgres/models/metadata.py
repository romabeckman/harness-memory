from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MetadataObject(BaseModel):
    value: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("value", mode="before")
    @classmethod
    def validate_object_root(cls, value):
        if not isinstance(value, dict):
            raise ValueError("metadata root must be a JSON object")
        return value


FoundationMetadata = MetadataObject
