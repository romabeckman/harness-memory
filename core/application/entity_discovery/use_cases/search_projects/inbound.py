from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


class SearchProjectsInput(BaseModel):
    key: Annotated[
        StrictStr | None,
        Field(max_length=255, description="Match one project key exactly."),
    ] = None
    query: Annotated[
        StrictStr | None,
        Field(
            max_length=255,
            description="Find a case-insensitive substring in project keys or names.",
        ),
    ] = None
    limit: StrictInt = Field(
        default=25,
        ge=1,
        le=100,
        description="Maximum number of results, from 1 to 100.",
    )
    offset: StrictInt = Field(
        default=0,
        ge=0,
        le=10000,
        description="Number of matching projects to skip.",
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("key", "query")
    @classmethod
    def trim_text_filter(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("search filter must not be empty")
        return value
