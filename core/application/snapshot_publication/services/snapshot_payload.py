from typing import Any

from core.domain.snapshot_publication.aggregates.project_knowledge_snapshot import (
    ProjectKnowledgeSnapshot,
)


def snapshot_payload(snapshot: ProjectKnowledgeSnapshot) -> dict[str, Any]:
    return {
        "schema_version": snapshot.schema_version.value,
        "project": {
            "key": snapshot.project.key.value,
            "name": snapshot.project.name,
            "metadata": snapshot.project.metadata.to_dict(),
        },
        "revision": snapshot.revision.value,
        "generated_at": snapshot.generated_at.value.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        ),
        "entities": [
            {
                "key": item.key.value,
                "type": item.type.value,
                "name": item.name,
                "canonical_key": item.canonical_key,
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
