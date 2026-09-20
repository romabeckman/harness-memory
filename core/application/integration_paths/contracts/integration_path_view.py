from pydantic import BaseModel, ConfigDict, StrictInt, model_validator

from ..types.path_traversal_direction import PathTraversalDirection
from .path_entity_view import PathEntityView
from .path_hop_view import PathHopView


class IntegrationPathView(BaseModel):
    entities: tuple[PathEntityView, ...]
    hops: tuple[PathHopView, ...] = ()
    hop_count: StrictInt

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_path_shape(self):
        if not self.entities:
            raise ValueError("integration path must contain at least one entity")
        if len(self.entities) != len(self.hops) + 1:
            raise ValueError("integration path entity and hop cardinality is inconsistent")
        if self.hop_count != len(self.hops):
            raise ValueError("integration path hop_count is inconsistent")
        entity_ids = tuple(item.entity.identity_id or item.entity.id for item in self.entities)
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError("integration path cannot repeat entities")
        for index, hop in enumerate(self.hops):
            if hop.traversal_direction is PathTraversalDirection.OUTBOUND:
                expected = (entity_ids[index], entity_ids[index + 1])
            else:
                expected = (entity_ids[index + 1], entity_ids[index])
            hop_endpoints = (
                hop.source.identity_id or hop.source.id,
                hop.target.identity_id or hop.target.id,
            )
            if hop_endpoints != expected:
                raise ValueError("integration path hop endpoints are inconsistent")
        return self
