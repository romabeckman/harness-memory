from pydantic import BaseModel, ConfigDict, Field, StrictInt


class ImpactAnalysisBounds(BaseModel):
    max_depth: StrictInt = Field(default=4, ge=1, le=8)
    max_consumers: StrictInt = Field(default=100, ge=1, le=500)
    max_paths: StrictInt = Field(default=25, ge=1, le=100)
    evidence_limit: StrictInt = Field(default=5, ge=0, le=20)
    owner_limit: StrictInt = Field(default=5, ge=0, le=20)
    max_result_bytes: StrictInt = Field(default=1024 * 1024, ge=64 * 1024, le=16 * 1024 * 1024)

    model_config = ConfigDict(frozen=True, extra="forbid")


ImpactBounds = ImpactAnalysisBounds
