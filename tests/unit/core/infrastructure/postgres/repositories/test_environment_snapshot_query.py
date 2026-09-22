from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.repositories.memory_resource_repository import (
    PostgresMemoryResourceRepository,
)


def test_reads_snapshot_entity_fingerprints_for_tenant() -> None:
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    snapshot_id = uuid4()
    project_id = uuid4()
    with Session(engine) as session:
        session.add(Project(id=project_id, tenant_id="tenant-a", key="catalog", name="Catalog"))
        session.add(
            Snapshot(
                id=snapshot_id,
                tenant_id="tenant-a",
                project_id=project_id,
                revision=1,
                schema_version="1.0",
                payload_hash="a" * 64,
                payload={},
                metadata_json={},
            )
        )
        session.add(
            Entity(
                id=uuid4(),
                identity_id=uuid4(),
                tenant_id="tenant-a",
                project_id=project_id,
                snapshot_id=snapshot_id,
                entity_key="catalog-api",
                entity_type="service",
                name="Catalog API",
                metadata_json={"version": "2"},
            )
        )
        session.commit()

    repository = PostgresMemoryResourceRepository(engine=engine)
    result = repository.get_snapshot_entity_fingerprints(snapshot_id, "tenant-a")

    assert set(result) == {"catalog-api"}
    assert len(result["catalog-api"]) == 64
    assert repository.get_snapshot_entity_fingerprints(snapshot_id, "tenant-b") == {}
