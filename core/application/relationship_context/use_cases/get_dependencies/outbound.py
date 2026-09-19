from pydantic import BaseModel, ConfigDict, StrictBool

from core.application.relationship_context.contracts.dependency_view import DependencyView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem


class GetDependenciesOutput(BaseModel):
    entity: EntityContextItem
    items: tuple[DependencyView, ...] = ()
    truncated: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")
