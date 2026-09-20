from uuid import UUID

from pydantic import ConfigDict

from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.types.relationship_query_bounds import (
    RelationshipQueryBounds,
)


class GetDependenciesInput(RelationshipQueryBounds):
    entity_id: UUID
    direction: RelationshipDirection = RelationshipDirection.BOTH

    model_config = ConfigDict(frozen=True, extra="forbid")
