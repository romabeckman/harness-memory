from typing import Literal

from pydantic import BaseModel, ConfigDict


class ResourceReadBounds(BaseModel):
    fact_limit: Literal[25] = 25
    evidence_limit: Literal[5] = 5

    model_config = ConfigDict(frozen=True, extra="forbid")
