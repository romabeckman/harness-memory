from unittest.mock import patch
from uuid import UUID, uuid4

from sqlalchemy import event
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.infrastructure.postgres.models import Base, Entity, Project, Relation, Snapshot
from core.infrastructure.postgres.repositories.integration_path_repository import (
    PostgresIntegrationPathRepository,
)

from .test_integration_path_traversal import _query, _repository, _seed


def test_visible_no_path_does_not_load_active_relation_hydration_rows():
    session_factory = _repository()
    ids = _seed(session_factory)
    repository = PostgresIntegrationPathRepository(session_factory)
    with patch.object(
        repository,
        "_load_active_relations",
        side_effect=AssertionError("no-path query must not hydrate all relations"),
    ):
        result = repository.find_paths(
            TenantScope("tenant-a"), _query(ids["source"], ids["disconnected"])
        )
    assert result.paths == ()


def test_recursive_path_query_orders_bounded_rows_before_global_expansion_limit():
    session_factory = _repository()
    ids = _seed(session_factory)
    engine = session_factory.kw["bind"]
    statements = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        if "integration_path_walk" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        repository = PostgresIntegrationPathRepository(session_factory)
        repository.find_paths(
            TenantScope("tenant-a"),
            _query(ids["source"], ids["middle"], max_depth=4, max_paths=1),
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    assert statements
    assert "ORDER BY" in statements[0].upper()
    assert "LIMIT" in statements[0].upper()


def test_owner_hydration_applies_owner_limit_inside_database_query():
    session_factory = _repository()
    ids = _seed(session_factory)
    engine = session_factory.kw["bind"]
    statements = []

    def record_statement(_connection, _cursor, statement, _parameters, _context, _executemany):
        if "owner_source" in statement:
            statements.append(statement)

    event.listen(engine, "before_cursor_execute", record_statement)
    try:
        result = PostgresIntegrationPathRepository(session_factory).find_paths(
            TenantScope("tenant-a"),
            _query(ids["source"], ids["middle"], owner_limit=1),
        )
    finally:
        event.remove(engine, "before_cursor_execute", record_statement)

    assert result.paths[0].entities[0].owners
    assert statements
    assert "ROW_NUMBER" in statements[0].upper()


def _comma_key_repository():
    from sqlalchemy import create_engine

    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant = "tenant-a"
    with session_factory() as session:
        project = Project(tenant_id=tenant, key="comma-project", name="Comma")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id=tenant,
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="c" * 64,
            payload={},
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        source = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="source",
            entity_type="service",
            name="Source",
            metadata_json={},
        )
        target = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="target",
            entity_type="service",
            name="Target",
            metadata_json={},
        )
        session.add_all([source, target])
        session.flush()
        routes = [
            ["a,b", "c", "d", "e"],
            ["a", "b,c", "d", "e"],
            ["a", "b", "c,d", "e"],
        ]
        route_entities_by_key = {}
        for route_keys in routes:
            for key in route_keys:
                route_entities_by_key.setdefault(
                    key,
                    Entity(
                        id=uuid4(),
                        tenant_id=tenant,
                        project_id=project.id,
                        snapshot_id=snapshot.id,
                        entity_key=key,
                        entity_type="service",
                        name=key,
                        metadata_json={},
                    ),
                )
        session.add_all(list(route_entities_by_key.values()))
        session.flush()
        for route_index, route_keys in enumerate(routes):
            route_entities = [route_entities_by_key[key] for key in route_keys]
            nodes = [source, *route_entities, target]
            session.add_all(
                [
                    Relation(
                        id=UUID(int=route_index * 10 + hop_index + 1),
                        tenant_id=tenant,
                        snapshot_id=snapshot.id,
                        source_entity_id=nodes[hop_index].id,
                        target_entity_id=nodes[hop_index + 1].id,
                        relation_type=RelationType.DEPENDS_ON.value,
                        provenance_kind="declared",
                        metadata_json={},
                    )
                    for hop_index in range(len(nodes) - 1)
                ]
            )
        session.commit()
    return session_factory, source.id, target.id


def test_comma_entity_keys_keep_deterministic_tuple_order_before_max_paths():
    session_factory, source_id, target_id = _comma_key_repository()
    result = PostgresIntegrationPathRepository(session_factory).find_paths(
        TenantScope("tenant-a"),
        _query(source_id, target_id, max_depth=5, max_paths=1),
    )
    assert result.termination_reason is PathTerminationReason.PATH_LIMIT
    assert [item.entity.key for item in result.paths[0].entities] == [
        "source",
        "a",
        "b",
        "c,d",
        "e",
        "target",
    ]
