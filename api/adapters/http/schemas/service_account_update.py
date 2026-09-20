from pydantic import BaseModel, ConfigDict, Field


class ServiceAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
