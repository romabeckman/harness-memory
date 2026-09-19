from pydantic import BaseModel, ConfigDict, Field, StrictInt


class RelationshipQueryBounds(BaseModel):
    limit: StrictInt = Field(default=25, ge=1, le=100)
    evidence_limit: StrictInt = Field(default=5, ge=0, le=20)

    model_config = ConfigDict(frozen=True, extra="forbid")
