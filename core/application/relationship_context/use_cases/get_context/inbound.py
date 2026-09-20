from uuid import UUID

from pydantic import ConfigDict

from core.application.relationship_context.types.relationship_query_bounds import (
    RelationshipQueryBounds,
)


class GetContextInput(RelationshipQueryBounds):
    entity_id: UUID

    model_config = ConfigDict(frozen=True, extra="forbid")
