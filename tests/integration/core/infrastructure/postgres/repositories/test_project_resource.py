from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.infrastructure.postgres.models import Base, Entity, Project, Snapshot
from core.infrastructure.postgres.repositories.memory_resource_repository import (
    PostgresMemoryResourceRepository,
)


def _repository():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed_project(session_factory):
    with session_factory() as session:
        project = Project(
            tenant_id="tenant-a", key="github.com/company/payments-api", name="Payments"
        )
        session.add(project)
        session.flush()
        historical = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="1" * 64,
            payload={"raw": "historical"},
            metadata_json={},
        )
        active = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=2,
            schema_version="1.0",
            payload_hash="2" * 64,
            payload={"raw": "active"},
            metadata_json={"source": "catalog"},
        )
        session.add_all([historical, active])
        session.flush()
        project.active_snapshot_id = active.id
        session.add_all(
            [
                Entity(
                    id=uuid4(),
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=active.id,
                    entity_key=f"entity-{index:02d}",
                    entity_type="service",
                    name=f"Entity {index}",
                    metadata_json={},
                )
                for index in range(27)
            ]
        )
        foreign_project = Project(tenant_id="tenant-b", key=project.key, name="Foreign")
        session.add(foreign_project)
        session.commit()
        return project.id, historical.id, active.id


def test_project_resource_reads_only_active_snapshot_and_reports_bounds():
    _, session_factory = _repository()
    _seed_project(session_factory)
    repository = PostgresMemoryResourceRepository(session_factory)

    result = repository.load_active_project(
        ProjectResourceInput(project_key="github.com/company/payments-api"),
        TenantScope("tenant-a"),
        ResourceReadBounds(),
    )

    assert result.project.revision == 2
    assert len(result.entities) == 25
    assert result.entities_truncated is True
    assert [entity.key for entity in result.entities] == [
        f"entity-{index:02d}" for index in range(25)
    ]


def test_project_resource_hides_foreign_tenant_as_not_found():
    _, session_factory = _repository()
    _seed_project(session_factory)
    repository = PostgresMemoryResourceRepository(session_factory)

    try:
        repository.load_active_project(
            ProjectResourceInput(project_key="github.com/company/payments-api"),
            TenantScope("tenant-b"),
            ResourceReadBounds(),
        )
    except ResourceNotFound:
        return
    raise AssertionError("foreign project must be indistinguishable from missing project")
