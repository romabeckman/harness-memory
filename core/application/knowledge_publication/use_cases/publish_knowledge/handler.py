from dataclasses import replace
from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

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
from core.application.snapshot_publication.services.payload_hash_calculator import (
    PayloadHashCalculator,
)
from core.application.snapshot_publication.services.snapshot_payload import snapshot_payload
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
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
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
        if raw_type not in EntityType._value2member_map_:
            raise ValueError(f"unsupported entity type: {raw_type}")
        entity_type = EntityType(raw_type)
        return EntityFact(
            EntityKey(item["key"]),
            entity_type,
            item.get("name", item["key"]),
            MetadataObject(item.get("metadata", {})),
            item.get("canonical_key"),
        )
    raw_type = getattr(item, "type", "service")
    if raw_type not in EntityType._value2member_map_:
        raise ValueError(f"unsupported entity type: {raw_type}")
    entity_type = EntityType(raw_type)
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
        if raw_type not in RelationType._value2member_map_:
            raise ValueError(f"unsupported relation type: {raw_type}")
        relation_type = RelationType(raw_type)
        raw_prov = item.get("provenance", "declared")
        if raw_prov not in ProvenanceKind._value2member_map_:
            raise ValueError(f"unsupported provenance: {raw_prov}")
        provenance = ProvenanceKind(raw_prov)
        return RelationFact(
            RelationReference(
                item.get("ref")
                or sha256(
                    (
                        f"{item['source_entity_key']}|{raw_type}|{item['target_entity_key']}|"
                        f"{raw_prov}|{sorted((item.get('metadata') or {}).items())}"
                    ).encode()
                ).hexdigest()
            ),
            EntityKey(item["source_entity_key"]),
            relation_type,
            EntityKey(item["target_entity_key"]),
            provenance,
            MetadataObject(item.get("metadata", {})),
        )
    raw_type = getattr(item, "type", "depends_on")
    if raw_type not in RelationType._value2member_map_:
        raise ValueError(f"unsupported relation type: {raw_type}")
    relation_type = RelationType(raw_type)
    raw_prov = getattr(item, "provenance", "declared")
    if raw_prov not in ProvenanceKind._value2member_map_:
        raise ValueError(f"unsupported provenance: {raw_prov}")
    provenance = ProvenanceKind(raw_prov)
    reference = getattr(item, "ref", getattr(item, "reference", None))
    if reference is None:
        reference = sha256(
            (
                f"{getattr(item, 'source_entity_key')}|{raw_type}|"
                f"{getattr(item, 'target_entity_key')}|{raw_prov}|"
                f"{sorted(getattr(item, 'metadata', {}).items())}"
            ).encode()
        ).hexdigest()
    return RelationFact(
        RelationReference(reference),
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
            revision_val = (
                int.from_bytes(sha256(input.version.encode()).digest()[:8], "big") % 2147483647 + 1
            )

        return ProjectKnowledgeSnapshot(
            schema_version=SchemaVersion("1.0"),
            project_key=ProjectKey(input.project_key),
            project_name=input.project_key,
            project_metadata=MetadataObject(input.metadata),
            revision=Revision(revision_val),
            generated_at=GeneratedAt(datetime.now(timezone.utc)),
            entities=tuple(_normalize_entity(e) for e in input.entities),
            relations=tuple(_normalize_relation(r) for r in input.relations),
            evidence=tuple(_normalize_evidence(ev) for ev in input.evidence),
        )

    def execute(self, input: PublishKnowledgeInput) -> PublishKnowledgeOutput:
        snapshot = self._build_snapshot(input)
        existing = self._publication_repository.find_by_deployment(
            project_key=input.project_key,
            env_name=input.environment_name,
            deployment_id=input.deployment_id,
            tenant_id=input.tenant_id,
        )
        if existing is not None and existing.snapshot_revision is not None:
            snapshot = replace(snapshot, revision=Revision(existing.snapshot_revision))
        content = snapshot_payload(snapshot)
        content.pop("generated_at", None)
        payload_hash = PayloadHashCalculator().calculate(content).value
        if existing is not None and existing.status == PublicationStatus.COMPLETED:
            if existing.payload_hash is not None and existing.payload_hash != payload_hash:
                raise RevisionConflict("deployment identity was reused with different content")
            return PublishKnowledgeOutput(
                publication_id=existing.id.value,
                snapshot_id=existing.snapshot_id,  # type: ignore[arg-type]
                status=PublicationStatus.ALREADY_PUBLISHED,
            )

        env = self._environment_repository.resolve_or_create(
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
            payload_hash=payload_hash,
        )

        publish_args = dict(
            tenant_id=input.tenant_id,
            publication=publication,
            snapshot=snapshot,
            environment_id=env.id,
        )
        if input.expected_current_snapshot_id is not None:
            publish_args["expected_current_snapshot_id"] = input.expected_current_snapshot_id
        new_snapshot_id = self._publication_repository.publish_atomically_with_environment(
            **publish_args
        )

        recorded = self._publication_repository.find_by_deployment(
            project_key=input.project_key,
            env_name=input.environment_name,
            deployment_id=input.deployment_id,
            tenant_id=input.tenant_id,
        )
        if recorded is not None and recorded.id != publication.id:
            return PublishKnowledgeOutput(
                publication_id=recorded.id.value,
                snapshot_id=new_snapshot_id,
                status=PublicationStatus.ALREADY_PUBLISHED,
            )

        return PublishKnowledgeOutput(
            publication_id=publication.id.value,
            snapshot_id=new_snapshot_id,
            status=PublicationStatus.COMPLETED,
        )
