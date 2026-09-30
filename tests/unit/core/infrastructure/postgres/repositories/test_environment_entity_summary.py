from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.models import Base, Entity, Environment, Project, Tenant
from core.infrastructure.postgres.repositories.environment_repository import (
    PostgresEnvironmentRepository,
)
from core.infrastructure.postgres.repositories.knowledge_read_repository import (
    KnowledgeReadRepository,
)


def test_summary_is_snapshot_scoped_bounded_and_connects_discovery():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    tenant_id, project_id, snapshot_id, older_id = (uuid4() for _ in range(4))
    with factory() as session:
        session.add(Tenant(id=tenant_id, key="tenant", name="Tenant"))
        session.add(Project(id=project_id, tenant_id=tenant_id, key="catalog"))
        session.add_all(
            [
                Environment(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    name="staging",
                    type="staging",
                    current_snapshot_id=snapshot_id,
                ),
                Environment(
                    tenant_id=tenant_id, project_id=project_id, name="production", type="production"
                ),
            ]
        )
        session.add_all(
            [
                Entity(
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=snapshot_id,
                    entity_key=f"service-{index:02}",
                    entity_type="service",
                    name=f"Service {index}",
                )
                for index in range(12)
            ]
        )
        session.add(
            Entity(
                tenant_id=tenant_id,
                project_id=project_id,
                snapshot_id=older_id,
                entity_key="old",
                entity_type="api",
            )
        )
        session.commit()

    repository = PostgresEnvironmentRepository(session_factory=factory)
    summary = repository.get_entity_summary(snapshot_id, str(tenant_id))
    assert summary["total_entities"] == 12
    assert summary["counts_by_type"] == {"service": 12}
    assert len(summary["items"]) == 10
    assert summary["has_more"] is True
    assert summary["items"][0]["key"] == "service-00"
    assert summary["items"][0]["entity_id"]
    assert repository.get_entity_summary(snapshot_id, str(uuid4()))["total_entities"] == 0
    assert repository.get_entity_summary(uuid4(), str(tenant_id))["has_more"] is False

    projects = KnowledgeReadRepository(factory).search_projects(
        TenantScope(str(tenant_id)), key="catalog", query=None, limit=10, offset=0
    )
    environments = {item.name: item for item in projects[0].environments}
    assert environments["staging"].entity_count == 12
    assert environments["staging"].environment_type == "staging"
    assert environments["production"].entity_count is None
