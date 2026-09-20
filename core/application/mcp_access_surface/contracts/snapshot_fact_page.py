from pydantic import BaseModel, ConfigDict, StrictBool

from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.relation_view import RelationView


class SnapshotFactPage(BaseModel):
    entities: tuple[EntityContextItem, ...] = ()
    relations: tuple[RelationView, ...] = ()
    evidence: tuple[EvidenceView, ...] = ()
    entities_truncated: StrictBool = False
    relations_truncated: StrictBool = False
    evidence_truncated: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")
