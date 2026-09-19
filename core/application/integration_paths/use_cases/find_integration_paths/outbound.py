from pydantic import BaseModel, ConfigDict, StrictBool

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem

from ...contracts.integration_path_view import IntegrationPathView
from ...types.path_termination_reason import PathTerminationReason


class FindIntegrationPathsOutput(BaseModel):
    source: EntityContextItem
    target: EntityContextItem
    paths: tuple[IntegrationPathView, ...] = ()
    truncated: StrictBool = False
    termination_reason: PathTerminationReason

    model_config = ConfigDict(frozen=True, extra="forbid")

