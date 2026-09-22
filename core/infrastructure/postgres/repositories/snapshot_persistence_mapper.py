from uuid import NAMESPACE_URL, UUID, uuid4, uuid5
from typing import Any

from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)
from core.application.snapshot_publication.services.snapshot_payload import snapshot_payload

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.relation import Relation
from ..models.snapshot import Snapshot
from .snapshot_graph_rows import SnapshotGraphRows


def _canonical_entity_id(
    tenant_id: str,
    project_key: str,
    entity_type: str,
    entity_key: str,
    canonical_key: str | None = None,
) -> UUID:
    identity_key = canonical_key or f"project:{project_key}:{entity_key}"
    return uuid5(NAMESPACE_URL, f"harness-memory:{tenant_id}:{entity_type}:{identity_key}")


class SnapshotPersistenceMapper:
    def map(
        self,
        snapshot: ProjectKnowledgeSnapshot,
        tenant_id: str,
        payload_hash: Any,
        project_id: UUID | None = None,
    ) -> SnapshotGraphRows:
        project_id = project_id or uuid4()
        snapshot_id = uuid4()
        entity_ids = {item.key.value: uuid4() for item in snapshot.entities}
        identity_ids = {
            item.key.value: _canonical_entity_id(
                tenant_id,
                snapshot.project.key.value,
                item.type.value,
                item.key.value,
                item.canonical_key,
            )
            for item in snapshot.entities
        }
        relation_ids = {item.reference.value: uuid4() for item in snapshot.relations}
        hash_value = payload_hash.value if hasattr(payload_hash, "value") else payload_hash
        snapshot_row = Snapshot(
            id=snapshot_id,
            tenant_id=tenant_id,
            project_id=project_id,
            revision=snapshot.revision.value,
            schema_version=snapshot.schema_version.value,
            payload_hash=hash_value,
            payload=snapshot_payload(snapshot),
            metadata_json=snapshot.project.metadata.to_dict(),
        )
        entities = tuple(
            Entity(
                id=entity_ids[item.key.value],
                tenant_id=tenant_id,
                identity_id=identity_ids[item.key.value],
                project_id=project_id,
                snapshot_id=snapshot_id,
                entity_key=item.key.value,
                entity_type=item.type.value,
                name=item.name,
                metadata_json=item.metadata.to_dict(),
            )
            for item in snapshot.entities
        )
        relations = tuple(
            Relation(
                id=relation_ids[item.reference.value],
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                source_entity_id=entity_ids[item.source_entity_key.value],
                target_entity_id=entity_ids[item.target_entity_key.value],
                source_identity_id=identity_ids[item.source_entity_key.value],
                target_identity_id=identity_ids[item.target_entity_key.value],
                relation_type=item.type.value,
                provenance_kind=item.provenance.value,
                metadata_json=item.metadata.to_dict(),
            )
            for item in snapshot.relations
        )
        evidence = tuple(
            Evidence(
                id=uuid4(),
                tenant_id=tenant_id,
                snapshot_id=snapshot_id,
                relation_id=(
                    relation_ids[item.relation_reference.value] if item.relation_reference else None
                ),
                source=item.source,
                excerpt=item.excerpt,
                metadata_json=item.metadata.to_dict(),
            )
            for item in snapshot.evidence
        )
        return SnapshotGraphRows(
            snapshot_row, entities, relations, evidence, entity_ids, identity_ids, relation_ids
        )
