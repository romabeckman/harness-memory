from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


class ImpactConsumerView(BaseModel):
    entity: EntityContextItem
    project: ProjectContextItem
    depth: StrictInt = Field(ge=1)
    relation_id: UUID
    relation_type: RelationType
    provenance: ProvenanceKind
    metadata: dict[str, Any] = Field(default_factory=dict)
    owners: tuple[EntityContextItem, ...] = ()
    evidence: tuple[EvidenceView, ...] = ()

    model_config = ConfigDict(frozen=True, extra="forbid")

    @property
    def consumer(self) -> EntityContextItem:
        return self.entity

    @property
    def path_depth(self) -> int:
        return self.depth

    @property
    def ownership(self) -> tuple[EntityContextItem, ...]:
        return self.owners
