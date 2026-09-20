from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.types.dependency_relation_type import (
    DependencyRelationType,
)
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind


class DependencyView(BaseModel):
    relation_id: UUID
    type: DependencyRelationType
    direction: RelationshipDirection
    peer: EntityContextItem
    provenance: ProvenanceKind
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: tuple[EvidenceView, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")
