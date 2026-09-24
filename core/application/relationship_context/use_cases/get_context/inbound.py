from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, model_validator


class GetContextInput(BaseModel):
    entity_id: UUID | None = None
    snapshot_id: UUID | None = None
    project_id: UUID | None = None
    tenant_id: StrictStr | None = Field(default=None, min_length=1, max_length=255)
    limit: StrictInt = Field(default=100, ge=1, le=500)
    result_limit: StrictInt = Field(default=25, ge=1, le=25)
    evidence_limit: StrictInt = Field(default=5, ge=0, le=20)
    offset: StrictInt = Field(default=0, ge=0, le=10000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def requires_selector(self):
        if all(
            value is None
            for value in (self.entity_id, self.snapshot_id, self.project_id, self.tenant_id)
        ):
            raise ValueError("provide entity_id, snapshot_id, project_id, or tenant_id")
        return self
