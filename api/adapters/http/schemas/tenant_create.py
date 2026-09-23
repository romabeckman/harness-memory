from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TenantText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class TenantCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: TenantText
    name: TenantText
    metadata: dict[str, Any] = Field(default_factory=dict)
