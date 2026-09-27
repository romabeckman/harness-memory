from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair
from core.infrastructure.postgres.models import Base, Project, Tenant
from core.infrastructure.postgres.repositories.project_link_repository import (
    PostgresProjectLinkRepository,
)


def _setup_db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory


def _seed_projects(session_factory):
    with session_factory() as session, session.begin():
        tenant1 = Tenant(id=uuid4(), key="t1", name="Tenant 1", status="active", metadata_json={})
        tenant2 = Tenant(id=uuid4(), key="t2", name="Tenant 2", status="active", metadata_json={})
        session.add_all([tenant1, tenant2])
        session.flush()

        p1 = Project(id=uuid4(), tenant_id=tenant1.id, key="proj-1", name="Project 1")
        p2 = Project(id=uuid4(), tenant_id=tenant1.id, key="proj-2", name="Project 2")
        p3 = Project(id=uuid4(), tenant_id=tenant2.id, key="proj-3", name="Project 3")
        session.add_all([p1, p2, p3])
        session.flush()
        return tenant1.id, tenant2.id, p1.id, p2.id, p3.id


def test_create_and_get_link_canonical():
    _, session_factory = _setup_db()
    _, _, p1_id, p2_id, _ = _seed_projects(session_factory)
    repo = PostgresProjectLinkRepository(session_factory)

    pair = CanonicalProjectPair(p2_id, p1_id)
    actor_id = uuid4()
    created = repo.create_link(pair, created_by=actor_id)

    assert isinstance(created, ProjectLink)
    assert created.pair == pair
    assert created.created_by == actor_id

    # Retrieve by pair
    retrieved = repo.get_link(CanonicalProjectPair(p1_id, p2_id))
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.pair == pair


def test_list_links_for_project_resolves_opposite_projects():
    _, session_factory = _setup_db()
    t1_id, t2_id, p1_id, p2_id, p3_id = _seed_projects(session_factory)
    repo = PostgresProjectLinkRepository(session_factory)

    # Link p1 with p2, and p3 with p1
    repo.create_link(CanonicalProjectPair(p1_id, p2_id))
    repo.create_link(CanonicalProjectPair(p3_id, p1_id))

    links_for_p1 = repo.list_links_for_project(p1_id)
    assert len(links_for_p1) == 2
    summaries = {summary.project_id: summary for summary in links_for_p1}

    assert p2_id in summaries
    assert summaries[p2_id].key == "proj-2"
    assert summaries[p2_id].name == "Project 2"
    assert summaries[p2_id].tenant_id == t1_id

    assert p3_id in summaries
    assert summaries[p3_id].key == "proj-3"
    assert summaries[p3_id].name == "Project 3"
    assert summaries[p3_id].tenant_id == t2_id


def test_delete_link_regardless_of_parameter_order():
    _, session_factory = _setup_db()
    _, _, p1_id, p2_id, _ = _seed_projects(session_factory)
    repo = PostgresProjectLinkRepository(session_factory)

    repo.create_link(CanonicalProjectPair(p1_id, p2_id))

    # Delete with reversed order
    result = repo.delete_link(CanonicalProjectPair(p2_id, p1_id))
    assert result is True

    # Link should no longer exist
    assert repo.get_link(CanonicalProjectPair(p1_id, p2_id)) is None

    # Deleting again returns False
    assert repo.delete_link(CanonicalProjectPair(p1_id, p2_id)) is False
