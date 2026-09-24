from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.entity_discovery.contracts.entity_search_criteria import EntitySearchCriteria
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.models import Base, Entity, Project, Snapshot, Tenant
from core.infrastructure.postgres.repositories.entity_search_repository import PostgresEntitySearchRepository
from core.infrastructure.postgres.repositories.knowledge_read_repository import KnowledgeReadRepository


def test_rest_and_mcp_search_same_current_document_set_and_literal_metadata_phrase():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_id = uuid4()
    with sessions() as session:
        session.add(Tenant(id=tenant_id, key="tenant", name="Tenant"))
        project = Project(tenant_id=tenant_id, key="docs")
        session.add(project)
        session.flush()
        old = Snapshot(tenant_id=tenant_id, project_id=project.id, revision=1,
                       schema_version="1.0", payload_hash="o" * 64, metadata_json={})
        current = Snapshot(tenant_id=tenant_id, project_id=project.id, revision=2,
                           schema_version="1.0", payload_hash="c" * 64, metadata_json={})
        session.add_all([old, current])
        session.flush()
        project.active_snapshot_id = current.id
        for snapshot, key, kind, lifecycle in [
            (old, "old", "feature", "active"),
            (current, "current", "feature", "active"),
            (current, "removed", "feature", "removed"),
            (current, "line", "document_revision", "active"),
        ]:
            session.add(Entity(tenant_id=tenant_id, project_id=project.id, snapshot_id=snapshot.id,
                               entity_key=key, entity_type=kind, name=key,
                               metadata_json={"content": "literal %_ phrase", "lifecycle": lifecycle}))
        session.commit()

    mcp = PostgresEntitySearchRepository(sessions).search(
        TenantScope(str(tenant_id)), EntitySearchCriteria(project="docs", query="%_"), None, 25
    )
    rest = KnowledgeReadRepository(sessions).entities(
        tenant_id=str(tenant_id), project_key="docs", snapshot_id=None,
        entity_type=None, entity_key=None, name=None, query="%_", limit=25, offset=0,
    )

    assert [item.key for item in mcp.items] == ["current"]
    assert [item["entity_key"] for item in rest] == ["current"]
