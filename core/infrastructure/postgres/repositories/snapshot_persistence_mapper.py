from datetime import timezone
from typing import Any
from uuid import UUID, uuid4

from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)

from ..models.entity import Entity
from ..models.evidence import Evidence
from ..models.relation import Relation
from ..models.snapshot import Snapshot
from .snapshot_graph_rows import SnapshotGraphRows


def _payload(snapshot: ProjectKnowledgeSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version.value,
        "project": {
            "key": snapshot.project.key.value,
            "name": snapshot.project.name,
            "metadata": snapshot.project.metadata.to_dict(),
        },
        "revision": snapshot.revision.value,
        "generated_at": snapshot.generated_at.value.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z"),
        "entities": [
            {
                "key": item.key.value,
                "type": item.type.value,
                "name": item.name,
                "metadata": item.metadata.to_dict(),
            }
            for item in snapshot.entities
        ],
        "relations": [
            {
                "ref": item.reference.value,
                "source_entity_key": item.source_entity_key.value,
                "type": item.type.value,
                "target_entity_key": item.target_entity_key.value,
                "provenance": item.provenance.value,
                "metadata": item.metadata.to_dict(),
            }
            for item in snapshot.relations
        ],
        "evidence": [
            {
                "source": item.source,
                "excerpt": item.excerpt,
                "relation_ref": item.relation_reference.value if item.relation_reference else None,
                "metadata": item.metadata.to_dict(),
            }
            for item in snapshot.evidence
        ],
    }


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
        relation_ids = {item.reference.value: uuid4() for item in snapshot.relations}
        hash_value = payload_hash.value if hasattr(payload_hash, "value") else payload_hash
        snapshot_row = Snapshot(
            id=snapshot_id,
            tenant_id=tenant_id,
            project_id=project_id,
            revision=snapshot.revision.value,
            schema_version=snapshot.schema_version.value,
            payload_hash=hash_value,
            payload=_payload(snapshot),
            metadata_json=snapshot.project.metadata.to_dict(),
        )
        entities = tuple(
            Entity(
                id=entity_ids[item.key.value],
                tenant_id=tenant_id,
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
            snapshot_row, entities, relations, evidence, entity_ids, relation_ids
        )
