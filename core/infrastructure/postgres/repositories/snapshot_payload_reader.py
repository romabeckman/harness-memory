from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.evidence import Evidence
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.relation import Relation
from core.infrastructure.postgres.models.snapshot import Snapshot


class SnapshotPayloadReader:
    def read(self, session: Session, snapshot: Snapshot) -> dict:
        entities = session.scalars(
            select(Entity)
            .where(Entity.snapshot_id == snapshot.id)
            .order_by(Entity.graph_position, Entity.id)
        ).all()
        relations = session.scalars(
            select(Relation)
            .where(Relation.snapshot_id == snapshot.id)
            .order_by(Relation.graph_position, Relation.id)
        ).all()
        evidence = session.scalars(
            select(Evidence)
            .where(Evidence.snapshot_id == snapshot.id)
            .order_by(Evidence.graph_position, Evidence.id)
        ).all()
        project_key, project_name = snapshot.project_key, snapshot.project_name
        if not project_key:
            project = session.get(Project, snapshot.project_id)
            if project is not None:
                project_key = project.key
                project_name = project.name

        entity_keys = {item.id: item.entity_key for item in entities}
        relation_refs = {item.id: item.relation_ref for item in relations}
        generated_at = snapshot.generated_at
        if generated_at.tzinfo is None:
            generated_at = generated_at.replace(tzinfo=timezone.utc)
        generated_at = generated_at.astimezone(timezone.utc)
        return {
            "schema_version": snapshot.schema_version,
            "project": {
                "key": project_key,
                "name": project_name,
                "metadata": snapshot.metadata_json,
            },
            "revision": snapshot.revision,
            "generated_at": generated_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "entities": [
                {
                    "key": item.entity_key,
                    "type": item.entity_type,
                    "name": item.name,
                    "canonical_key": item.canonical_key,
                    "metadata": item.metadata_json,
                }
                for item in entities
            ],
            "relations": [
                {
                    "ref": item.relation_ref,
                    "source_entity_key": entity_keys[item.source_entity_id],
                    "type": item.relation_type,
                    "target_entity_key": entity_keys[item.target_entity_id],
                    "provenance": item.provenance_kind,
                    "metadata": item.metadata_json,
                }
                for item in relations
            ],
            "evidence": [
                {
                    "source": item.source,
                    "excerpt": item.excerpt,
                    "relation_ref": (
                        relation_refs[item.relation_id] if item.relation_id is not None else None
                    ),
                    "metadata": item.metadata_json,
                }
                for item in evidence
            ],
        }
