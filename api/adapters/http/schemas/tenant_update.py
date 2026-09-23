from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

TenantName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class TenantUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: TenantName | None = None
    status: Literal["active", "disabled"] | None = None
    metadata: dict[str, Any] | None = None
