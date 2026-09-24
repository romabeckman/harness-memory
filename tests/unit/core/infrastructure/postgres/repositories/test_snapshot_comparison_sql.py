from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models import Base, Entity, Project, Snapshot
from core.infrastructure.postgres.repositories.memory_resource_repository import PostgresMemoryResourceRepository


def test_snapshot_comparison_pages_in_database_and_returns_totals():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    project_id, source_id, target_id = uuid4(), uuid4(), uuid4()
    with Session(engine) as session:
        session.add(Project(id=project_id, tenant_id="tenant-a", key="catalog"))
        session.add_all([
            Snapshot(id=source_id, tenant_id="tenant-a", project_id=project_id,
                     revision=1, schema_version="1.0", payload_hash="a" * 64, metadata_json={}),
            Snapshot(id=target_id, tenant_id="tenant-a", project_id=project_id,
                     revision=2, schema_version="1.0", payload_hash="b" * 64, metadata_json={}),
        ])
        for snapshot_id, keys in [(source_id, ("a", "b", "same", "modified")),
                                  (target_id, ("old", "same", "modified"))]:
            for key in keys:
                session.add(Entity(tenant_id="tenant-a", project_id=project_id,
                                   snapshot_id=snapshot_id, entity_key=key, entity_type="service",
                                   metadata_json={"version": 2 if key == "modified" and snapshot_id == source_id else 1}))
        session.commit()

    result = PostgresMemoryResourceRepository(engine=engine).compare_snapshot_entities(
        source_id, target_id, "tenant-a", offset=1, limit=1
    )

    assert result["added"] == ("b",)
    assert result["removed"] == ()
    assert result["modified"] == ()
    assert result["unchanged"] == ()
    assert result["total_added"] == 2
    assert result["total_removed"] == 1
    assert result["total_modified"] == 1
    assert result["total_unchanged"] == 1
