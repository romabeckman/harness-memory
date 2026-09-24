from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, model_validator

from .outbound import GetContextOutput


class GetContextPage(BaseModel):
    items: tuple[GetContextOutput, ...]
    count: StrictInt = Field(ge=0)
    limit: StrictInt = Field(ge=1, le=25)
    offset: StrictInt = Field(ge=0)
    has_more: StrictBool

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def respects_limit(self):
        if len(self.items) != self.count or self.count > self.limit:
            raise ValueError("context page exceeds requested limit")
        return self
