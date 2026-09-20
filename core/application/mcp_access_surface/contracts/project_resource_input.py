from pydantic import BaseModel, ConfigDict, Field, StrictStr


class ProjectResourceInput(BaseModel):
    project_key: StrictStr = Field(min_length=1, max_length=255)

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)
