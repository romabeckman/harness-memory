from datetime import datetime, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models import Base, Entity, Evidence, Project, Relation, Snapshot
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.repositories.knowledge_publication_repository import (
    PostgresKnowledgePublicationRepository,
)


def test_baseline_is_current_snapshot_for_requested_tenant_project_environment():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        project = Project(id=uuid4(), tenant_id="tenant-a", key="demo", name="Demo")
        session.add(project)
        session.flush()
        env = Environment(
            id=uuid4(),
            tenant_id="tenant-a",
            project_id=project.id,
            name="production",
            type="production",
        )
        session.add(env)
        session.flush()
        snapshot_metadata = {"nodes": [{"id": "feature:orders"}], "edges": []}
        snapshot = Snapshot(
            id=uuid4(),
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=env.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            project_key="demo",
            project_name="Demo",
            generated_at=datetime(2026, 9, 17, 12, tzinfo=timezone.utc),
            metadata_json=snapshot_metadata,
        )
        session.add(snapshot)
        session.flush()
        service = Entity(
            id=uuid4(),
            tenant_id="tenant-a",
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="feature:orders",
            entity_type="feature",
            canonical_key="feature:orders",
            graph_position=0,
            metadata_json={"content": "Full document"},
        )
        api = Entity(
            id=uuid4(),
            tenant_id="tenant-a",
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="service:orders",
            entity_type="service",
            canonical_key="service:orders",
            graph_position=1,
            metadata_json={"content": "Orders service"},
        )
        session.add_all([service, api])
        session.flush()
        relation = Relation(
            id=uuid4(),
            tenant_id="tenant-a",
            snapshot_id=snapshot.id,
            source_entity_id=service.id,
            target_entity_id=api.id,
            relation_type="uses",
            provenance_kind="declared",
            relation_ref="orders-uses-service",
            graph_position=0,
            metadata_json={"scope": "runtime"},
        )
        session.add(relation)
        session.flush()
        session.add(
            Evidence(
                id=uuid4(),
                tenant_id="tenant-a",
                snapshot_id=snapshot.id,
                relation_id=relation.id,
                source="architecture.md",
                excerpt="Orders uses the shared service.",
                graph_position=0,
                metadata_json={"section": 2},
            )
        )
        env.current_snapshot_id = snapshot.id
        session.commit()
    repo = PostgresKnowledgePublicationRepository(engine=engine)
    result = repo.load_latest_graph("demo", "production", "tenant-a")
    assert result["graph"]["entities"][0]["metadata"]["content"] == "Full document"
    assert result["graph"]["entities"][0]["canonical_key"] == "feature:orders"
    assert result["graph"]["relations"][0]["ref"] == "orders-uses-service"
    assert result["graph"]["evidence"][0]["relation_ref"] == "orders-uses-service"
    assert result["graph"]["metadata"] == snapshot_metadata
    for project_key, environment, tenant in [
        ("demo", "staging", "tenant-a"),
        ("demo", "production", "tenant-b"),
    ]:
        with pytest.raises(LookupError):
            repo.load_latest_graph(project_key, environment, tenant)
