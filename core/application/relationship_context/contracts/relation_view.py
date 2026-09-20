from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


class RelationView(BaseModel):
    id: UUID
    type: RelationType
    direction: RelationshipDirection
    source: EntityContextItem
    target: EntityContextItem
    provenance: ProvenanceKind
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: tuple[EvidenceView, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")
