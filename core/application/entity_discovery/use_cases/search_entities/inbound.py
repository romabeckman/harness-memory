from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StrictStr,
    field_validator,
)

from core.domain.snapshot_publication.types.entity_type import EntityType


class SearchEntitiesInput(BaseModel):
    key: Annotated[
        StrictStr | None,
        Field(max_length=255, description="Match an entity's stable key exactly."),
    ] = None
    name: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description="Match names that start with this text, ignoring case.",
        ),
    ] = None
    type: EntityType | None = Field(
        default=None, description="Restrict results to one entity type."
    )
    project: Annotated[
        StrictStr | None,
        Field(max_length=255, description="Match one project key exactly."),
    ] = None
    limit: StrictInt = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results in this page, from 1 to 100.",
    )
    cursor: Annotated[
        StrictStr | None,
        Field(
            max_length=1024,
            description="Opaque continuation token returned by the previous page.",
        ),
    ] = None

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
