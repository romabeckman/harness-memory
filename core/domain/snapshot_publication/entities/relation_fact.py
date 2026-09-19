from dataclasses import dataclass

from ..types.provenance_kind import ProvenanceKind
from ..types.relation_type import RelationType
from ..value_objects.entity_key import EntityKey
from ..value_objects.metadata_object import MetadataObject
from ..value_objects.relation_reference import RelationReference


@dataclass(frozen=True, slots=True, init=False)
class RelationFact:
    reference: RelationReference
    source_entity_key: EntityKey
    type: RelationType
    target_entity_key: EntityKey
    provenance: ProvenanceKind
    metadata: MetadataObject

    def __init__(
        self,
        reference: RelationReference | None = None,
        source_entity_key: EntityKey | None = None,
        type: RelationType | None = None,
        target_entity_key: EntityKey | None = None,
        provenance: ProvenanceKind | None = None,
        metadata: MetadataObject | None = None,
        *,
        ref: RelationReference | None = None,
        source: EntityKey | None = None,
        relation_type: RelationType | None = None,
        target: EntityKey | None = None,
    ) -> None:
        object.__setattr__(self, "reference", reference or ref)
        object.__setattr__(self, "source_entity_key", source_entity_key or source)
        object.__setattr__(self, "type", type or relation_type)
        object.__setattr__(self, "target_entity_key", target_entity_key or target)
        object.__setattr__(self, "provenance", provenance)
        object.__setattr__(self, "metadata", metadata or MetadataObject({}))

    @property
    def ref(self) -> RelationReference:
        return self.reference

    @property
    def relation_type(self) -> RelationType:
        return self.type

    @property
    def source(self) -> EntityKey:
        return self.source_entity_key

    @property
    def target(self) -> EntityKey:
        return self.target_entity_key
