from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.infrastructure.postgres.models import Base, Entity, Project, Snapshot
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)


def _repository():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine), engine


def _seed(session_factory):
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="payments", name="Payments")
        session.add(project)
        session.flush()
        other_project = Project(tenant_id="tenant-b", key="payments", name="Payments")
        session.add(other_project)
        session.flush()
        old = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="1" * 64,
            metadata_json={},
        )
        active = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=2,
            schema_version="1.0",
            payload_hash="2" * 64,
            metadata_json={},
        )
        other_snapshot = Snapshot(
            tenant_id="tenant-b",
            project_id=other_project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="3" * 64,
            metadata_json={},
        )
        session.add_all([old, active, other_snapshot])
        session.flush()
        project.active_snapshot_id = active.id
        other_project.active_snapshot_id = other_snapshot.id
        session.add_all(
            [
                Entity(
                    id=uuid4(),
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=old.id,
                    entity_key="old-api",
                    entity_type="api",
                    name="Old API",
                    metadata_json={},
                ),
                Entity(
                    id=uuid4(),
                    identity_id=UUID(int=100),
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=active.id,
                    entity_key="payments-api",
                    entity_type="api",
                    name="GET /payments/{id}",
                    metadata_json={"content": "The service uses PostgreSQL for persistence."},
                ),
                Entity(
                    id=uuid4(),
                    tenant_id="tenant-b",
                    project_id=other_project.id,
                    snapshot_id=other_snapshot.id,
                    entity_key="payments-api",
                    entity_type="api",
                    name="Payments API",
                    metadata_json={},
                ),
            ]
        )
        session.commit()


def test_repository_returns_active_tenant_rows_with_exact_project_filter():
    session_factory, _ = _repository()
    _seed(session_factory)
    repository = PostgresEntitySearchRepository(session_factory)

    result = repository.search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(name="payments", type=EntityType.API, project="payments"),
        None,
        25,
    )

    assert [item.key for item in result.items] == ["payments-api"]
    assert result.items[0].revision == 2
    assert result.items[0].project_key == "payments"
    assert result.items[0].entity_id == UUID(int=100)

    project_exact = repository.search(
        TenantScope("tenant-a"), EntitySearchCriteria(project="payments"), None, 25
    )
    assert [item.key for item in project_exact.items] == ["payments-api"]

    project_fragment = repository.search(
        TenantScope("tenant-a"), EntitySearchCriteria(project="pay"), None, 25
    )
    assert project_fragment.items == ()


def test_repository_searches_document_metadata_content_and_combines_exact_project_filter():
    session_factory, _ = _repository()
    _seed(session_factory)
    repository = PostgresEntitySearchRepository(session_factory)

    result = repository.search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(query="postgresql", project="payments"),
        None,
        25,
    )

    assert [item.key for item in result.items] == ["payments-api"]

    no_match = repository.search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(query="postgresql", project="pay"),
        None,
        25,
    )
    assert no_match.items == ()


def test_admin_scope_searches_across_tenants():
    session_factory, _ = _repository()
    _seed(session_factory)
    result = PostgresEntitySearchRepository(session_factory).search(
        TenantScope("*", is_admin=True), EntitySearchCriteria(key="payments-api"), None, 25
    )

    assert len(result.items) == 2


def test_repository_escapes_name_wildcards_and_paginates_without_duplicates():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="p", name="P")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a", project_id=project.id, revision=1, schema_version="1.0",
            payload_hash="a" * 64, metadata_json={}
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        for key, name in [
            ("a", r"Rate_100%!\b"),
            ("b", r"RateX1000!\b"),
            ("c", r"Rate-100%!\b"),
        ]:
            session.add(Entity(
                tenant_id="tenant-a", project_id=project.id, snapshot_id=snapshot.id,
                entity_key=key, entity_type="service", name=name, metadata_json={}
            ))
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    criteria = EntitySearchCriteria(name=r"Rate_100%!\b")
    first = repository.search(TenantScope("tenant-a"), criteria, None, 1)
    second = repository.search(
        TenantScope("tenant-a"), criteria, first.next_cursor, 1
    ) if first.next_cursor else None

    assert [item.name for item in first.items] == [r"Rate_100%!\b"]
    assert second is None or second.items == ()


def test_repository_keyset_cursor_traverses_all_rows_once():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="p", name="P")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a", project_id=project.id, revision=1, schema_version="1.0",
            payload_hash="b" * 64, metadata_json={}
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        for key in ["a", "b", "c", "d"]:
            session.add(Entity(
                tenant_id="tenant-a", project_id=project.id, snapshot_id=snapshot.id,
                entity_key=key, entity_type="service", name=key, metadata_json={}
            ))
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    criteria = EntitySearchCriteria(type=EntityType.SERVICE)
    cursor = None
    keys = []
    while True:
        page = repository.search(TenantScope("tenant-a"), criteria, cursor, 2)
        keys.extend(item.key for item in page.items)
        if page.next_cursor is None:
            break
        cursor = page.next_cursor

    assert keys == ["a", "b", "c", "d"]


def test_repository_does_not_mutate_persistence():
    session_factory, _ = _repository()
    _seed(session_factory)
    with session_factory() as session:
        before = (
            session.query(Project).count(),
            session.query(Snapshot).count(),
            session.query(Entity).count(),
        )
    PostgresEntitySearchRepository(session_factory).search(
        TenantScope("tenant-a"), EntitySearchCriteria(key="payments-api"), None, 25
    )
    with session_factory() as session:
        after = (
            session.query(Project).count(),
            session.query(Snapshot).count(),
            session.query(Entity).count(),
        )
    assert before == after
