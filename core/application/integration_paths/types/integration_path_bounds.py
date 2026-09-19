from pydantic import BaseModel, ConfigDict, Field, StrictInt


class IntegrationPathBounds(BaseModel):
    max_depth: StrictInt = Field(default=4, ge=1, le=8)
    max_paths: StrictInt = Field(default=10, ge=1, le=25)
    evidence_limit: StrictInt = Field(default=5, ge=0, le=20)
    owner_limit: StrictInt = Field(default=5, ge=0, le=20)

    model_config = ConfigDict(frozen=True, extra="forbid")

