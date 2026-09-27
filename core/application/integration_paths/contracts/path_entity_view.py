from pydantic import BaseModel, ConfigDict

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem

from .ownership_view import OwnershipView


class PathEntityView(BaseModel):
    entity: EntityContextItem
    owners: tuple[OwnershipView, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")
