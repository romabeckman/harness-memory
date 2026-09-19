from pydantic import BaseModel, ConfigDict, Field, StrictInt, model_validator

from core.application.entity_discovery.value_objects.search_cursor import SearchCursor

from .entity_search_item import EntitySearchItem


class EntitySearchPage(BaseModel):
    items: tuple[EntitySearchItem, ...] = ()
    next_cursor: SearchCursor | None = None
    limit: StrictInt = Field(ge=1, le=100)

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    @model_validator(mode="after")
    def respects_limit(self):
        if len(self.items) > self.limit:
            raise ValueError("entity search page exceeds requested limit")
        if not self.items and self.next_cursor is not None:
            raise ValueError("empty entity search page cannot have a cursor")
        return self

    @property
    def count(self) -> int:
        return len(self.items)
