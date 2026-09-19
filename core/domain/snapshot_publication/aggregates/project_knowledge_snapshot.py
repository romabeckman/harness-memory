from dataclasses import dataclass

from ..entities.entity_fact import EntityFact
from ..entities.evidence_fact import EvidenceFact
from ..entities.project_descriptor import ProjectDescriptor
from ..entities.relation_fact import RelationFact
from ..errors.snapshot_invariant_violation import SnapshotInvariantViolation
from ..value_objects.generated_at import GeneratedAt
from ..value_objects.metadata_object import MetadataObject
from ..value_objects.project_key import ProjectKey
from ..value_objects.revision import Revision
from ..value_objects.schema_version import SchemaVersion


@dataclass(frozen=True, slots=True, init=False)
class ProjectKnowledgeSnapshot:
    schema_version: SchemaVersion
    project: ProjectDescriptor
    revision: Revision
    generated_at: GeneratedAt
    entities: tuple[EntityFact, ...]
    relations: tuple[RelationFact, ...]
    evidence: tuple[EvidenceFact, ...]

    @property
    def project_key(self) -> ProjectKey:
        return self.project.key

    def __init__(
        self,
        schema_version: SchemaVersion,
        project: ProjectDescriptor | None = None,
        revision: Revision | None = None,
        generated_at: GeneratedAt | None = None,
        entities: tuple[EntityFact, ...] = (),
        relations: tuple[RelationFact, ...] = (),
        evidence: tuple[EvidenceFact, ...] = (),
        *,
        project_key: ProjectKey | None = None,
        project_name: str | None = None,
        project_metadata: MetadataObject | None = None,
    ) -> None:
        if project is None:
            if project_key is None or project_metadata is None:
                raise TypeError("project descriptor is required")
            project = ProjectDescriptor(project_key, project_name, project_metadata)
        object.__setattr__(self, "schema_version", schema_version)
        object.__setattr__(self, "project", project)
        object.__setattr__(self, "revision", revision)
        object.__setattr__(self, "generated_at", generated_at)
        object.__setattr__(self, "entities", tuple(entities))
        object.__setattr__(self, "relations", tuple(relations))
        object.__setattr__(self, "evidence", tuple(evidence))
        self._validate()

    def _validate(self) -> None:
        if not isinstance(self.schema_version, SchemaVersion):
            raise SnapshotInvariantViolation("invalid schema version")
        if not isinstance(self.revision, Revision):
            raise SnapshotInvariantViolation("invalid revision")
        if not isinstance(self.generated_at, GeneratedAt):
            raise SnapshotInvariantViolation("invalid generated_at")
        entity_keys = [fact.key.value for fact in self.entities]
        if len(entity_keys) != len(set(entity_keys)):
            raise SnapshotInvariantViolation("duplicate entity key")
        canonical_keys = [
            (fact.type.value, fact.canonical_key or fact.key.value) for fact in self.entities
        ]
        if len(canonical_keys) != len(set(canonical_keys)):
            raise SnapshotInvariantViolation("duplicate canonical entity identity")
        relation_refs = [fact.reference.value for fact in self.relations]
        if len(relation_refs) != len(set(relation_refs)):
            raise SnapshotInvariantViolation("duplicate relation reference")
        entity_key_set = set(entity_keys)
        for relation in self.relations:
            if relation.source_entity_key.value not in entity_key_set:
                raise SnapshotInvariantViolation(
                    f"unresolved source entity key: {relation.source_entity_key.value}"
                )
            if relation.target_entity_key.value not in entity_key_set:
                raise SnapshotInvariantViolation(
                    f"unresolved target entity key: {relation.target_entity_key.value}"
                )
        relation_ref_set = set(relation_refs)
        for item in self.evidence:
            if (
                item.relation_reference is not None
                and item.relation_reference.value not in relation_ref_set
            ):
                raise SnapshotInvariantViolation(
                    f"unresolved relation reference: {item.relation_reference.value}"
                )
