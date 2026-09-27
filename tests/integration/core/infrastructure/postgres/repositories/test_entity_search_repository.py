from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.infrastructure.postgres.models import (
    Base,
    Entity,
    Environment,
    KnowledgePublication,
    Project,
    Snapshot,
)
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
        other_project = Project(tenant_id="tenant-b", key="other-payments", name="Payments")
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
    narrowed = PostgresEntitySearchRepository(session_factory).search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(key="payments-api", tenant_id="tenant-b"),
        None,
        25,
    )
    assert narrowed.items == ()


def test_repository_escapes_name_wildcards_and_paginates_without_duplicates():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="p", name="P")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        for key, name in [
            ("a", r"Rate_100%!\b"),
            ("b", r"RateX1000!\b"),
            ("c", r"Rate-100%!\b"),
        ]:
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key=key,
                    entity_type="service",
                    name=name,
                    metadata_json={},
                )
            )
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    criteria = EntitySearchCriteria(name=r"Rate_100%!\b")
    first = repository.search(TenantScope("tenant-a"), criteria, None, 1)
    second = (
        repository.search(TenantScope("tenant-a"), criteria, first.next_cursor, 1)
        if first.next_cursor
        else None
    )

    assert [item.name for item in first.items] == [r"Rate_100%!\b"]
    assert second is None or second.items == ()


def test_repository_keyset_cursor_traverses_all_rows_once():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="p", name="P")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="b" * 64,
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        for key in ["a", "b", "c", "d"]:
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key=key,
                    entity_type="service",
                    name=key,
                    metadata_json={},
                )
            )
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


def test_current_search_hides_removed_documents_and_revision_lines_but_history_can_find_them():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="docs")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="c" * 64,
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        for key, kind, lifecycle in [
            ("current", "feature", "active"),
            ("deleted", "feature", "removed"),
            ("old-line", "document_revision", "active"),
        ]:
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key=key,
                    entity_type=kind,
                    name="needle",
                    metadata_json={
                        "content": "needle",
                        "lifecycle": lifecycle,
                    },
                )
            )
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    current = repository.search(
        TenantScope("tenant-a"), EntitySearchCriteria(query="needle"), None, 25
    )
    history = repository.search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(query="needle", include_history=True),
        None,
        25,
    )

    assert [item.key for item in current.items] == ["current"]
    assert [item.key for item in history.items] == ["current", "deleted", "old-line"]


def test_duplicate_canonical_ids_across_projects_paginate_by_physical_occurrence():
    session_factory, _ = _repository()
    with session_factory() as session:
        for project_key in ("alpha", "beta"):
            project = Project(tenant_id="tenant-a", key=project_key)
            session.add(project)
            session.flush()
            snapshot = Snapshot(
                tenant_id="tenant-a",
                project_id=project.id,
                revision=1,
                schema_version="1.0",
                payload_hash=project_key[0] * 64,
                metadata_json={},
            )
            session.add(snapshot)
            session.flush()
            project.active_snapshot_id = snapshot.id
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key="shared",
                    entity_type="service",
                    identity_id=UUID(int=123),
                    metadata_json={},
                )
            )
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    criteria = EntitySearchCriteria(key="shared")
    first = repository.search(TenantScope("tenant-a"), criteria, None, 1)
    second = repository.search(TenantScope("tenant-a"), criteria, first.next_cursor, 1)

    assert len(first.items) == len(second.items) == 1
    assert first.items[0].entity_id == second.items[0].entity_id == UUID(int=123)
    assert first.items[0].occurrence_id != second.items[0].occurrence_id
    assert {first.items[0].project_key, second.items[0].project_key} == {"alpha", "beta"}
    assert second.next_cursor is None


def test_environment_selection_and_cursor_keep_original_snapshot_after_promotion():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="catalog")
        session.add(project)
        session.flush()
        production = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="p" * 64,
            metadata_json={},
        )
        staging = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            revision=2,
            schema_version="1.0",
            payload_hash="s" * 64,
            metadata_json={},
        )
        session.add_all([production, staging])
        session.flush()
        project.active_snapshot_id = production.id
        environment = Environment(
            tenant_id="tenant-a",
            project_id=project.id,
            name="staging",
            type="staging",
            current_snapshot_id=staging.id,
        )
        session.add(environment)
        for snapshot, keys in [(production, ("prod",)), (staging, ("a", "b"))]:
            for key in keys:
                session.add(
                    Entity(
                        tenant_id="tenant-a",
                        project_id=project.id,
                        snapshot_id=snapshot.id,
                        entity_key=key,
                        entity_type="service",
                        metadata_json={},
                    )
                )
        session.commit()
        original_snapshot_id = staging.id
        project_id = project.id

    repository = PostgresEntitySearchRepository(session_factory)
    criteria = EntitySearchCriteria(project="catalog", tenant_id="tenant-a", environment="staging")
    first = repository.search(TenantScope("tenant-a"), criteria, None, 1)
    with session_factory() as session:
        project = session.get(Project, project_id)
        environment = (
            session.query(Environment).filter_by(project_id=project_id, name="staging").one()
        )
        next_snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project_id,
            revision=3,
            schema_version="1.0",
            payload_hash="n" * 64,
            metadata_json={},
        )
        session.add(next_snapshot)
        session.flush()
        environment.current_snapshot_id = next_snapshot.id
        project.active_snapshot_id = next_snapshot.id
        session.add(
            Entity(
                tenant_id="tenant-a",
                project_id=project_id,
                snapshot_id=next_snapshot.id,
                entity_key="c",
                entity_type="service",
                metadata_json={},
            )
        )
        session.commit()

    second = repository.search(TenantScope("tenant-a"), criteria, first.next_cursor, 1)
    refreshed = repository.search(TenantScope("tenant-a"), criteria, None, 25)

    assert [item.key for item in first.items] == ["a"]
    assert [item.key for item in second.items] == ["b"]
    assert second.items[0].snapshot_id == original_snapshot_id
    assert [item.key for item in refreshed.items] == ["c"]


def test_project_search_uses_current_snapshot_from_each_environment():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="catalog")
        session.add(project)
        session.flush()
        production = Environment(
            tenant_id="tenant-a", project_id=project.id, name="production", type="production"
        )
        staging = Environment(
            tenant_id="tenant-a", project_id=project.id, name="staging", type="staging"
        )
        session.add_all([production, staging])
        session.flush()
        production_old = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=production.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            metadata_json={},
        )
        production_current = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=production.id,
            revision=2,
            schema_version="1.0",
            payload_hash="b" * 64,
            metadata_json={},
        )
        staging_old = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=staging.id,
            revision=1,
            schema_version="1.0",
            payload_hash="c" * 64,
            metadata_json={},
        )
        staging_current = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=staging.id,
            revision=2,
            schema_version="1.0",
            payload_hash="d" * 64,
            metadata_json={},
        )
        session.add_all([production_old, production_current, staging_old, staging_current])
        session.flush()
        production.current_snapshot_id = production_current.id
        staging.current_snapshot_id = staging_current.id
        project.active_snapshot_id = production_old.id
        for snapshot, key in (
            (production_old, "production-old"),
            (production_current, "production-current"),
            (staging_old, "staging-old"),
            (staging_current, "staging-current"),
        ):
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key=key,
                    entity_type="service",
                    metadata_json={},
                )
            )
        session.commit()

    result = PostgresEntitySearchRepository(session_factory).search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(project="catalog", tenant_id="tenant-a"),
        None,
        25,
    )

    assert {item.key for item in result.items} == {"production-current", "staging-current"}
    assert {item.environment_name for item in result.items} == {"production", "staging"}
    assert all(item.is_current_snapshot for item in result.items)


def test_unpublished_environment_does_not_fall_back_to_project_active_snapshot():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="catalog")
        session.add(project)
        session.flush()
        environment = Environment(
            tenant_id="tenant-a", project_id=project.id, name="production", type="production"
        )
        session.add(environment)
        session.flush()
        snapshot = Snapshot(
            tenant_id="tenant-a",
            project_id=project.id,
            environment_id=environment.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        session.add(
            Entity(
                tenant_id="tenant-a",
                project_id=project.id,
                snapshot_id=snapshot.id,
                entity_key="stale",
                entity_type="service",
                metadata_json={},
            )
        )
        session.commit()

    result = PostgresEntitySearchRepository(session_factory).search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(project="catalog", tenant_id="tenant-a"),
        None,
        25,
    )

    assert result.items == ()


def test_past_snapshot_search_returns_bounded_occurrences_with_publication_context():
    session_factory, _ = _repository()
    with session_factory() as session:
        project = Project(tenant_id="tenant-a", key="payments")
        session.add(project)
        session.flush()
        environment = Environment(
            tenant_id="tenant-a", project_id=project.id, name="production", type="production"
        )
        session.add(environment)
        session.flush()
        snapshots = []
        for revision, version in ((1, "1.0.0"), (2, "2.0.0")):
            publication_id = uuid4()
            snapshot = Snapshot(
                tenant_id="tenant-a",
                project_id=project.id,
                environment_id=environment.id,
                publication_id=publication_id,
                revision=revision,
                schema_version="1.0",
                payload_hash=str(revision) * 64,
                metadata_json={},
            )
            session.add(snapshot)
            session.flush()
            session.add(
                KnowledgePublication(
                    id=publication_id,
                    tenant_id="tenant-a",
                    project_id=project.id,
                    environment_id=environment.id,
                    deployment_id=f"deploy-{revision}",
                    version=version,
                    status="COMPLETED",
                    snapshot_id=snapshot.id,
                )
            )
            session.add(
                Entity(
                    tenant_id="tenant-a",
                    project_id=project.id,
                    snapshot_id=snapshot.id,
                    entity_key="payments-api",
                    entity_type="api",
                    name="Payments API",
                    metadata_json={},
                )
            )
            snapshots.append(snapshot)
        project.active_snapshot_id = snapshots[-1].id
        environment.current_snapshot_id = snapshots[-1].id
        snapshot_ids = {snapshot.id for snapshot in snapshots}
        session.commit()

    repository = PostgresEntitySearchRepository(session_factory)
    scope = TenantScope("tenant-a")
    current = repository.search(
        scope, EntitySearchCriteria(query="payments", type=EntityType.API), None, 25
    )
    history_criteria = EntitySearchCriteria(
        query="payments", type=EntityType.API, include_past_snapshots=True
    )
    first = repository.search(scope, history_criteria, None, 1)
    second = repository.search(scope, history_criteria, first.next_cursor, 1)

    assert len(current.items) == 1
    assert current.items[0].is_current_snapshot is True
    assert {item.snapshot_id for item in (*first.items, *second.items)} == snapshot_ids
    assert {item.publication_version for item in (*first.items, *second.items)} == {
        "1.0.0",
        "2.0.0",
    }
    assert {item.environment_name for item in (*first.items, *second.items)} == {"production"}
    assert {item.is_current_snapshot for item in (*first.items, *second.items)} == {True, False}
    assert all(item.publication_id is not None for item in (*first.items, *second.items))
    assert {item.publication_status for item in (*first.items, *second.items)} == {"COMPLETED"}
    assert second.next_cursor is None
    in_environment = repository.search(
        scope,
        EntitySearchCriteria(
            query="payments", environment="production", include_past_snapshots=True
        ),
        None,
        25,
    )
    assert {item.snapshot_id for item in in_environment.items} == snapshot_ids


def test_past_snapshot_search_respects_tenant_scope():
    session_factory, _ = _repository()
    _seed(session_factory)
    repository = PostgresEntitySearchRepository(session_factory)

    result = repository.search(
        TenantScope("tenant-a"),
        EntitySearchCriteria(project="payments", type=EntityType.API, include_past_snapshots=True),
        None,
        25,
    )

    assert {item.key for item in result.items} == {"old-api", "payments-api"}
    assert len({item.tenant_id for item in result.items}) == 1
