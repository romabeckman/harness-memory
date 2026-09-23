from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models import Base, Project, Snapshot
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
            payload={
                "schema_version": "1.0",
                "entities": [
                    {
                        "key": "feature:orders",
                        "type": "feature",
                        "metadata": {"content": "Full document"},
                    }
                ],
                "relations": [],
                "evidence": [],
            },
            metadata_json=snapshot_metadata,
        )
        session.add(snapshot)
        session.flush()
        env.current_snapshot_id = snapshot.id
        session.commit()
    repo = PostgresKnowledgePublicationRepository(engine=engine)
    result = repo.load_latest_graph("demo", "production", "tenant-a")
    assert result["graph"]["entities"][0]["metadata"]["content"] == "Full document"
    assert result["graph"]["metadata"] == snapshot_metadata
    for project_key, environment, tenant in [
        ("demo", "staging", "tenant-a"),
        ("demo", "production", "tenant-b"),
    ]:
        with pytest.raises(LookupError):
            repo.load_latest_graph(project_key, environment, tenant)
