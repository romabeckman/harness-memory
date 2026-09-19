from typing import Any

from ..aggregates.project_knowledge_snapshot import ProjectKnowledgeSnapshot
from ..entities.entity_fact import EntityFact
from ..entities.evidence_fact import EvidenceFact
from ..entities.project_descriptor import ProjectDescriptor
from ..entities.relation_fact import RelationFact
from ..types.entity_type import EntityType
from ..types.provenance_kind import ProvenanceKind
from ..types.relation_type import RelationType
from ..value_objects.entity_key import EntityKey
from ..value_objects.generated_at import GeneratedAt
from ..value_objects.metadata_object import MetadataObject
from ..value_objects.project_key import ProjectKey
from ..value_objects.relation_reference import RelationReference
from ..value_objects.revision import Revision
from ..value_objects.schema_version import SchemaVersion


def _metadata(value: Any) -> MetadataObject:
    return value if isinstance(value, MetadataObject) else MetadataObject(value or {})


class SnapshotBuilder:
    def build(self, request: Any = None, **values: Any) -> ProjectKnowledgeSnapshot:
        if request is not None and not values:
            project_input = request.project
            project = ProjectDescriptor(
                ProjectKey(project_input.key), project_input.name, _metadata(project_input.metadata)
            )
            entities = tuple(
                EntityFact(
                    EntityKey(item.key), EntityType(item.type), item.name, _metadata(item.metadata)
                )
                for item in request.entities
            )
            relations = tuple(
                RelationFact(
                    RelationReference(item.ref),
                    EntityKey(item.source_entity_key),
                    RelationType(item.type),
                    EntityKey(item.target_entity_key),
                    ProvenanceKind(item.provenance),
                    _metadata(item.metadata),
                )
                for item in request.relations
            )
            evidence = tuple(
                EvidenceFact(
                    item.source,
                    item.excerpt,
                    RelationReference(item.relation_ref) if item.relation_ref is not None else None,
                    _metadata(item.metadata),
                )
                for item in request.evidence
            )
            return ProjectKnowledgeSnapshot(
                SchemaVersion(request.schema_version),
                project,
                Revision(request.revision),
                GeneratedAt(request.generated_at),
                entities,
                relations,
                evidence,
            )
        return ProjectKnowledgeSnapshot(**values)

    execute = build


BuildProjectKnowledgeSnapshot = SnapshotBuilder
