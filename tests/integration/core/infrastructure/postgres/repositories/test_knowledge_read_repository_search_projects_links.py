from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.infrastructure.postgres.models import Base, Project, ProjectLinkModel, Tenant
from core.infrastructure.postgres.repositories.knowledge_read_repository import (
    KnowledgeReadRepository,
)


def _setup_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory


def _seed_data(session_factory):
    with session_factory() as session, session.begin():
        t1 = Tenant(id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={})
        t2 = Tenant(id=uuid4(), key="tenant-2", name="Tenant 2", status="active", metadata_json={})
        session.add_all([t1, t2])
        session.flush()

        p_alpha = Project(id=uuid4(), tenant_id=t1.id, key="alpha", name="Alpha Service")
        p_beta = Project(id=uuid4(), tenant_id=t1.id, key="beta", name="Beta Service")
        p_gamma = Project(id=uuid4(), tenant_id=t2.id, key="gamma", name="Gamma Cross Service")
        p_isolated = Project(id=uuid4(), tenant_id=t1.id, key="isolated", name="Isolated Service")
        session.add_all([p_alpha, p_beta, p_gamma, p_isolated])
        session.flush()

        # Link alpha -> beta (project_a=alpha, project_b=beta)
        link1 = ProjectLinkModel(id=uuid4(), project_a_id=p_alpha.id, project_b_id=p_beta.id)
        # Link gamma -> alpha (project_a=gamma, project_b=alpha) - opposite direction and cross-tenant
        link2 = ProjectLinkModel(id=uuid4(), project_a_id=p_gamma.id, project_b_id=p_alpha.id)
        session.add_all([link1, link2])
        session.flush()

        return t1, t2, p_alpha, p_beta, p_gamma, p_isolated


def test_search_projects_populates_bidirectional_and_cross_tenant_links():
    _, session_factory = _setup_db()
    t1, t2, p_alpha, p_beta, p_gamma, p_isolated = _seed_data(session_factory)
    repository = KnowledgeReadRepository(session_factory)

    scope = TenantScope(str(t1.id), is_admin=False)
    results = repository.search_projects(scope, key="alpha", query=None, limit=10, offset=0)

    assert len(results) == 1
    alpha_item = results[0]
    assert alpha_item.key == "alpha"
    assert len(alpha_item.links) == 2

    # Links should be ordered by name ASC, project_id ASC:
    # "Beta Service" vs "Gamma Cross Service"
    assert alpha_item.links[0].project_id == p_beta.id
    assert alpha_item.links[0].name == "Beta Service"
    assert str(alpha_item.links[0].tenant_id) == str(t1.id)

    assert alpha_item.links[1].project_id == p_gamma.id
    assert alpha_item.links[1].name == "Gamma Cross Service"
    assert str(alpha_item.links[1].tenant_id) == str(t2.id)


def test_search_projects_returns_empty_links_tuple_when_no_links():
    _, session_factory = _setup_db()
    t1, _, _, _, _, p_isolated = _seed_data(session_factory)
    repository = KnowledgeReadRepository(session_factory)

    scope = TenantScope(str(t1.id), is_admin=False)
    results = repository.search_projects(scope, key="isolated", query=None, limit=10, offset=0)

    assert len(results) == 1
    assert results[0].links == ()


def test_search_projects_batch_loads_links_for_multiple_projects():
    _, session_factory = _setup_db()
    t1, _, p_alpha, p_beta, _, p_isolated = _seed_data(session_factory)
    repository = KnowledgeReadRepository(session_factory)

    scope = TenantScope(str(t1.id), is_admin=False)
    results = repository.search_projects(scope, key=None, query=None, limit=10, offset=0)

    by_key = {item.key: item for item in results}
    assert "alpha" in by_key
    assert "beta" in by_key
    assert "isolated" in by_key

    # alpha has 2 links (beta and gamma)
    assert len(by_key["alpha"].links) == 2
    # beta has 1 link (alpha)
    assert len(by_key["beta"].links) == 1
    assert by_key["beta"].links[0].project_id == p_alpha.id
    assert by_key["beta"].links[0].name == "Alpha Service"
    # isolated has 0 links
    assert by_key["isolated"].links == ()
