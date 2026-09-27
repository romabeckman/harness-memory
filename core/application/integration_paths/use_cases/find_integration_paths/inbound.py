from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ...types.integration_path_bounds import IntegrationPathBounds


class FindIntegrationPathsInput(BaseModel):
    source_entity_id: UUID
    target_entity_id: UUID
    bounds: IntegrationPathBounds = Field(default_factory=IntegrationPathBounds)

    model_config = ConfigDict(frozen=True, extra="forbid")
