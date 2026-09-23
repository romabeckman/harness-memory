from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .project_search_item import ProjectSearchItem


class ProjectSearchPage(BaseModel):
    items: tuple[ProjectSearchItem, ...] = ()
    count: StrictInt = Field(ge=0)
    limit: StrictInt = Field(ge=1, le=100)
    offset: StrictInt = Field(ge=0, le=10000)
    has_more: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_count(self):
        if self.count != len(self.items) or self.count > self.limit:
            raise ValueError("project search count must match bounded items")
        return self
