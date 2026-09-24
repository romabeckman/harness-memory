from uuid import UUID

from pydantic import ConfigDict, Field, StrictStr

from core.application.relationship_context.types.relationship_query_bounds import (
    RelationshipQueryBounds,
)


class GetContextInput(RelationshipQueryBounds):
    entity_id: UUID
    snapshot_id: UUID | None = None
    project_id: UUID | None = None
    tenant_id: StrictStr | None = Field(default=None, min_length=1, max_length=255)

    model_config = ConfigDict(frozen=True, extra="forbid")
