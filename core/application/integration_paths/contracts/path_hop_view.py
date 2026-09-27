from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.application.integration_paths.types.path_traversal_direction import (
    PathTraversalDirection,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


class PathHopView(BaseModel):
    relation_id: UUID
    type: RelationType
    source: EntityContextItem
    target: EntityContextItem
    traversal_direction: PathTraversalDirection
    provenance: ProvenanceKind
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: tuple[EvidenceView, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")
