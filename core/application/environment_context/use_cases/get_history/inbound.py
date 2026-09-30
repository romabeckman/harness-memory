from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr, field_validator


class GetHistoryInput(BaseModel):
    project_key: StrictStr = Field(min_length=1, max_length=255)
    environment: StrictStr = Field(min_length=1, max_length=64)
    tenant_id: StrictStr | None = Field(default=None, max_length=255)
    snapshot_id: UUID | None = None
    query: StrictStr | None = Field(default=None, max_length=255)
    limit: StrictInt = Field(default=100, ge=1, le=500)
    offset: StrictInt = Field(default=0, ge=0, le=10000)

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("project_key", "environment", "tenant_id", "query")
    @classmethod
    def reject_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("selector must not be blank")
        return value
