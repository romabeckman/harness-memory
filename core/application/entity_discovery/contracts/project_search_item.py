from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictStr


class ProjectSearchItem(BaseModel):
    key: StrictStr = Field(min_length=1, max_length=255)
    name: StrictStr | None = Field(default=None, max_length=255)
    has_active_snapshot: StrictBool

    model_config = ConfigDict(frozen=True, extra="forbid")
