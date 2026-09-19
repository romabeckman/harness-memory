from dataclasses import dataclass
from uuid import UUID

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.relation import Relation
from ..models.snapshot import Snapshot


@dataclass(frozen=True, slots=True)
class SnapshotGraphRows:
    snapshot: Snapshot
    entities: tuple[Entity, ...]
    relations: tuple[Relation, ...]
    evidence: tuple[Evidence, ...]
    entity_ids: dict[str, UUID]
    relation_ids: dict[str, UUID]
