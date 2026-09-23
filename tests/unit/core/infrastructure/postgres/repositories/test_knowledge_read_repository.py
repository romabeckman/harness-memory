from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.models import Base, Project, Tenant
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

    assert [project.key for project in exact] == ["send"]
    assert [project.key for project in by_name] == ["send"]
    assert exact[0].has_active_snapshot is False
