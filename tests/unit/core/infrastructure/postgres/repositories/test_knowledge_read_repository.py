from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.models import Base, Environment, Project, Tenant
from core.infrastructure.postgres.repositories.knowledge_read_repository import (
    KnowledgeReadRepository,
)


def test_project_search_supports_exact_key_and_partial_name_without_snapshot():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    tenant_id = uuid4()
    with session_factory() as session:
        session.add(Tenant(id=tenant_id, key="tenant-a", name="Tenant A"))
        session.add_all(
            [
                Project(tenant_id=tenant_id, key="send", name="Send Platform"),
                Project(tenant_id=tenant_id, key="sender", name="Sender Service"),
            ]
        )
        session.commit()

    repository = KnowledgeReadRepository(session_factory)

    scope = TenantScope(str(tenant_id))
    exact = repository.search_projects(
        scope, key="send", query=None, limit=25, offset=0
    )
    by_name = repository.search_projects(
        scope, key=None, query="platform", limit=25, offset=0
    )
    unfiltered = repository.search_projects(
        scope, key=None, query=None, limit=1, offset=1
    )

    assert [project.key for project in exact] == ["send"]
    assert [project.key for project in by_name] == ["send"]
    assert [project.key for project in unfiltered] == ["sender"]
    assert exact[0].has_active_snapshot is False


def test_project_discovery_attributes_duplicate_keys_and_lists_environments():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    tenants = (uuid4(), uuid4())
    with session_factory() as session:
        for index, tenant_id in enumerate(tenants):
            session.add(Tenant(id=tenant_id, key=f"tenant-{index}", name=f"Tenant {index}"))
            project = Project(tenant_id=tenant_id, key="shared", name="Shared")
            session.add(project)
            session.flush()
            session.add(Environment(tenant_id=tenant_id, project_id=project.id,
                                    name="staging", type="staging"))
        session.commit()

    rows = KnowledgeReadRepository(session_factory).search_projects(
        TenantScope("*", is_admin=True), key="shared", query=None, limit=25, offset=0
    )

    assert len(rows) == 2
    assert {item.tenant_id for item in rows} == {str(tenant) for tenant in tenants}
    assert {item.tenant_key for item in rows} == {"tenant-0", "tenant-1"}
    assert len({item.project_id for item in rows}) == 2
    assert all(item.environment_names == ("staging",) for item in rows)
