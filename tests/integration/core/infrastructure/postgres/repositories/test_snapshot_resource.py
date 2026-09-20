from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.infrastructure.postgres.models import Base, Entity, Evidence, Project, Relation, Snapshot
from core.infrastructure.postgres.repositories.memory_resource_repository import (
    PostgresMemoryResourceRepository,
)


def _repository():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed_snapshot(session_factory):
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="payments", name="Payments")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            payload={"secret": "do-not-return"},
            metadata_json={"origin": "test"},
        )
        newer = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=2,
            schema_version="1.0",
            payload_hash="b" * 64,
            payload={},
            metadata_json={},
        )
        session.add_all([snapshot, newer])
        session.flush()
        project.active_snapshot_id = newer.id
        entities = [
            Entity(
                id=uuid4(),
                tenant_id="tenant-a",
                project_id=project.id,
                snapshot_id=snapshot.id,
                entity_key=f"entity-{index:02d}",
                entity_type="service",
                name=None,
                metadata_json={},
            )
            for index in range(30)
        ]
        session.add_all(entities)
        session.flush()
        relations = [
            Relation(
                id=uuid4(),
                tenant_id="tenant-a",
                snapshot_id=snapshot.id,
                source_entity_id=entities[index].id,
                target_entity_id=entities[index + 1].id,
                relation_type="depends_on",
                provenance_kind="declared",
                metadata_json={},
            )
            for index in range(29)
        ]
        session.add_all(relations)
        session.flush()
        session.add_all(
            [
                Evidence(
                    id=uuid4(),
                    tenant_id="tenant-a",
                    snapshot_id=snapshot.id,
                    relation_id=relations[0].id,
                    source=f"evidence-{index}",
                    excerpt=None,
                    metadata_json={},
                )
                for index in range(7)
            ]
        )
        session.commit()
        return snapshot.id, newer.id, project.id


def test_snapshot_resource_is_bounded_and_does_not_return_raw_payload_or_activate_snapshot():
    engine, session_factory = _repository()
    snapshot_id, active_id, project_id = _seed_snapshot(session_factory)
    repository = PostgresMemoryResourceRepository(session_factory)

    result = repository.load_snapshot(
        SnapshotResourceInput(snapshot_id=snapshot_id),
        TenantScope("tenant-a"),
        ResourceReadBounds(),
    )

    assert result.snapshot.revision == 1
    assert len(result.facts.entities) == 25
    assert len(result.facts.relations) == 25
    assert len(result.facts.evidence) == 5
    assert result.facts.entities_truncated is True
    assert result.facts.relations_truncated is True
    assert result.facts.evidence_truncated is True
    assert "secret" not in str(result.model_dump())
    with session_factory() as session:
        assert (
            session.scalar(select(Project.active_snapshot_id).where(Project.id == project_id))
            == active_id
        )


def test_snapshot_resource_hides_foreign_tenant_snapshot():
    _, session_factory = _repository()
    snapshot_id, _, _ = _seed_snapshot(session_factory)
    repository = PostgresMemoryResourceRepository(session_factory)

    try:
        repository.load_snapshot(
            SnapshotResourceInput(snapshot_id=snapshot_id),
            TenantScope("tenant-b"),
            ResourceReadBounds(),
        )
    except ResourceNotFound:
        return
    raise AssertionError("foreign snapshot must be indistinguishable from missing snapshot")
