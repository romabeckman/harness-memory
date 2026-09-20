from pydantic import BaseModel, ConfigDict, Field, StrictInt

from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem


class SearchEntitiesOutput(BaseModel):
    items: tuple[EntitySearchItem, ...] = ()
    count: StrictInt = Field(ge=0)
    limit: StrictInt = Field(ge=1, le=100)
    next_cursor: str | None = None

    model_config = ConfigDict(frozen=True, extra="forbid")
