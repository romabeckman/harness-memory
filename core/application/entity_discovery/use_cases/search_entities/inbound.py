from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from core.domain.snapshot_publication.types.entity_type import EntityType


class SearchEntitiesInput(BaseModel):
    key: Annotated[StrictStr | None, Field(max_length=255)] = None
    name: Annotated[StrictStr | None, Field(max_length=255)] = None
    type: EntityType | None = None
    project: Annotated[StrictStr | None, Field(max_length=255)] = None
    limit: StrictInt = Field(default=25, ge=1, le=100)
    cursor: Annotated[StrictStr | None, Field(max_length=1024)] = None

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "name", "project")
    @classmethod
    def trim_text_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("search filter must not be empty")
        return value

    @model_validator(mode="after")
    def require_filter(self):
        if self.key is None and self.name is None and self.type is None and self.project is None:
            raise ValueError("at least one discovery filter is required")
        return self
