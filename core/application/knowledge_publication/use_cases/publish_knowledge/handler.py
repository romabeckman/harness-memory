from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from core.application.environment_context.ports.environment_repository import (
    EnvironmentRepository,
)
from core.application.knowledge_publication.ports.knowledge_publication_repository import (
    KnowledgePublicationRepository,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import (
    PublishKnowledgeInput,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.outbound import (
    PublishKnowledgeOutput,
)
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.knowledge_publication.aggregates.knowledge_publication import (
    KnowledgePublication,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.knowledge_publication.value_objects.deployment_id import DeploymentId
from core.domain.knowledge_publication.value_objects.publication_id import PublicationId
from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.domain.snapshot_publication.entities.entity_fact import EntityFact
from core.domain.snapshot_publication.entities.evidence_fact import EvidenceFact
from core.domain.snapshot_publication.entities.relation_fact import RelationFact
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.domain.snapshot_publication.value_objects.entity_key import EntityKey
from core.domain.snapshot_publication.value_objects.generated_at import GeneratedAt
from core.domain.snapshot_publication.value_objects.metadata_object import MetadataObject
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.domain.snapshot_publication.value_objects.relation_reference import RelationReference
from core.domain.snapshot_publication.value_objects.revision import Revision
from core.domain.snapshot_publication.value_objects.schema_version import SchemaVersion


def _normalize_entity(item: Any) -> EntityFact:
    if isinstance(item, EntityFact):
        return item
    if isinstance(item, dict):
        raw_type = item.get("type", "service")
        entity_type = (
            EntityType(raw_type)
            if raw_type in EntityType._value2member_map_
            else EntityType.SERVICE
        )
        return EntityFact(
            EntityKey(item["key"]),
            entity_type,
            item.get("name", item["key"]),
            MetadataObject(item.get("metadata", {})),
            item.get("canonical_key"),
        )
    raw_type = getattr(item, "type", "service")
    entity_type = (
        EntityType(raw_type)
        if raw_type in EntityType._value2member_map_
        else EntityType.SERVICE
    )
    return EntityFact(
        EntityKey(getattr(item, "key")),
        entity_type,
        getattr(item, "name", getattr(item, "key")),
        MetadataObject(getattr(item, "metadata", {})),
        getattr(item, "canonical_key", None),
    )


def _normalize_relation(item: Any) -> RelationFact:
    if isinstance(item, RelationFact):
        return item
    if isinstance(item, dict):
        raw_type = item.get("type", "depends_on")
        relation_type = (
            RelationType(raw_type)
            if raw_type in RelationType._value2member_map_
            else RelationType.DEPENDS_ON
        )
        raw_prov = item.get("provenance", "declared")
        provenance = (
            ProvenanceKind(raw_prov)
            if raw_prov in ProvenanceKind._value2member_map_
            else ProvenanceKind.DECLARED
        )
        return RelationFact(
            RelationReference(item.get("ref", str(uuid4()))),
            EntityKey(item["source_entity_key"]),
            relation_type,
            EntityKey(item["target_entity_key"]),
            provenance,
            MetadataObject(item.get("metadata", {})),
        )
    raw_type = getattr(item, "type", "depends_on")
    relation_type = (
        RelationType(raw_type)
        if raw_type in RelationType._value2member_map_
        else RelationType.DEPENDS_ON
    )
    raw_prov = getattr(item, "provenance", "declared")
    provenance = (
        ProvenanceKind(raw_prov)
        if raw_prov in ProvenanceKind._value2member_map_
        else ProvenanceKind.DECLARED
    )
    return RelationFact(
        RelationReference(getattr(item, "ref", getattr(item, "reference", str(uuid4())))),
        EntityKey(getattr(item, "source_entity_key")),
        relation_type,
        EntityKey(getattr(item, "target_entity_key")),
        provenance,
        MetadataObject(getattr(item, "metadata", {})),
    )


def _normalize_evidence(item: Any) -> EvidenceFact:
    if isinstance(item, EvidenceFact):
        return item
    if isinstance(item, dict):
        rel_ref = item.get("relation_ref")
        return EvidenceFact(
            item.get("source", "ci/pipeline"),
            item.get("excerpt", ""),
            RelationReference(rel_ref) if rel_ref else None,
            MetadataObject(item.get("metadata", {})),
        )
    rel_ref = getattr(item, "relation_ref", None)
    return EvidenceFact(
        getattr(item, "source", "ci/pipeline"),
        getattr(item, "excerpt", ""),
        RelationReference(rel_ref) if rel_ref else None,
        MetadataObject(getattr(item, "metadata", {})),
    )


class PublishKnowledgeHandler:
    def __init__(
        self,
        publication_repository: KnowledgePublicationRepository,
        environment_repository: EnvironmentRepository,
    ) -> None:
        self._publication_repository = publication_repository
        self._environment_repository = environment_repository

    def _build_snapshot(self, input: PublishKnowledgeInput) -> ProjectKnowledgeSnapshot:
        try:
            revision_val = int(input.version)
        except (ValueError, TypeError):
            revision_val = abs(hash(input.version)) % 1000000 + 1

        return ProjectKnowledgeSnapshot(
            schema_version=SchemaVersion("1.0"),
            project_key=ProjectKey(input.project_key),
            project_name=input.project_key,
            project_metadata=MetadataObject({}),
            revision=Revision(revision_val),
            generated_at=GeneratedAt(datetime.now(timezone.utc)),
            entities=tuple(_normalize_entity(e) for e in input.entities),
            relations=tuple(_normalize_relation(r) for r in input.relations),
            evidence=tuple(_normalize_evidence(ev) for ev in input.evidence),
        )

    def execute(self, input: PublishKnowledgeInput) -> PublishKnowledgeOutput:
        existing = self._publication_repository.find_by_deployment(
            project_key=input.project_key,
            env_name=input.environment_name,
            deployment_id=input.deployment_id,
            tenant_id=input.tenant_id,
        )
        if existing is not None and existing.status == PublicationStatus.COMPLETED:
            return PublishKnowledgeOutput(
                publication_id=existing.id.value,
                snapshot_id=existing.snapshot_id,  # type: ignore[arg-type]
                status=PublicationStatus.ALREADY_PUBLISHED,
            )

        env = self._environment_repository.resolve(
            project_key=input.project_key,
            name=input.environment_name,
            tenant_id=input.tenant_id,
        )
        if env is None:
            raise ValueError(f"environment {input.environment_name} not found")

        pub_id = PublicationId.generate()
        publication = KnowledgePublication(
            id=pub_id,
            project_key=ProjectKey(input.project_key),
            environment_name=EnvironmentName(input.environment_name),
            deployment_id=DeploymentId(input.deployment_id),
            version=input.version,
        )

        snapshot = self._build_snapshot(input)

        new_snapshot_id = self._publication_repository.publish_atomically_with_environment(
            tenant_id=input.tenant_id,
            publication=publication,
            snapshot=snapshot,
            environment_id=env.id,
        )

        return PublishKnowledgeOutput(
            publication_id=publication.id.value,
            snapshot_id=new_snapshot_id,
            status=PublicationStatus.COMPLETED,
        )
