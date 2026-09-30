from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from core.application.environment_context.use_cases.get_history.inbound import GetHistoryInput
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.entity import Entity
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.repositories.environment_history_repository import (
    PostgresEnvironmentHistoryRepository,
)


@pytest.fixture
def history_repository():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_id, other_tenant_id = uuid4(), uuid4()
    project_id, environment_id = uuid4(), uuid4()
    first_id, second_id = uuid4(), uuid4()
    with Session(engine) as session:
        session.add_all(
            [
                Tenant(id=tenant_id, key="main", name="Main", status="active"),
                Tenant(id=other_tenant_id, key="other", name="Other", status="active"),
                Project(id=project_id, tenant_id=tenant_id, key="catalog", name="Catalog"),
            ]
        )
        session.flush()
        environment = Environment(
            id=environment_id,
            tenant_id=tenant_id,
            project_id=project_id,
            name="production",
            type="production",
        )
        session.add(environment)
        session.flush()
        session.add_all(
            [
                Snapshot(
                    id=first_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    environment_id=environment_id,
                    revision=1,
                    schema_version="1.0",
                    payload_hash="first",
                    project_key="catalog",
                ),
                Snapshot(
                    id=second_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    environment_id=environment_id,
                    revision=2,
                    schema_version="1.0",
                    payload_hash="second",
                    project_key="catalog",
                ),
            ]
        )
        session.flush()
        session.add_all(
            [
                Entity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=first_id,
                    entity_key="removed",
                    entity_type="service",
                    name="Removed",
                    metadata_json={},
                ),
                Entity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=first_id,
                    entity_key="changed",
                    entity_type="service",
                    name="Before",
                    metadata_json={"description": "authentication old"},
                ),
                Entity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=second_id,
                    entity_key="changed",
                    entity_type="service",
                    name="After",
                    metadata_json={"description": "authentication new"},
                ),
                Entity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=project_id,
                    snapshot_id=second_id,
                    entity_key="added",
                    entity_type="service",
                    name="Added",
                    metadata_json={},
                ),
            ]
        )
        first_publication_id, second_publication_id = uuid4(), uuid4()
        session.add_all(
            [
                KnowledgePublication(
                    id=first_publication_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    environment_id=environment_id,
                    deployment_id="first",
                    version="1.0.0",
                    status="COMPLETED",
                    snapshot_id=first_id,
                ),
                KnowledgePublication(
                    id=second_publication_id,
                    tenant_id=tenant_id,
                    project_id=project_id,
                    environment_id=environment_id,
                    deployment_id="second",
                    version="2.0.0",
                    status="COMPLETED",
                    snapshot_id=second_id,
                ),
            ]
        )
        session.get(Snapshot, first_id).publication_id = first_publication_id
        session.get(Snapshot, second_id).publication_id = second_publication_id
        environment.current_snapshot_id = second_id
        session.commit()
    yield (
        PostgresEnvironmentHistoryRepository(factory),
        tenant_id,
        other_tenant_id,
        first_id,
        second_id,
    )
    engine.dispose()


def test_history_lists_latest_revision_and_pages_snapshots(history_repository):
    repository, tenant_id, _, first_id, second_id = history_repository

    first_page = repository.get_history(
        GetHistoryInput(
            project_key="catalog", environment="production", tenant_id=str(tenant_id), limit=1
        )
    )
    second_page = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            limit=1,
            offset=1,
        )
    )

    assert first_page["current_snapshot_id"] == str(second_id)
    assert [item["snapshot_id"] for item in first_page["snapshots"]] == [str(second_id)]
    assert first_page["snapshots"][0]["is_current"] is True
    assert first_page["has_more"] is True
    assert [item["snapshot_id"] for item in second_page["snapshots"]] == [str(first_id)]
    assert second_page["snapshots"][0]["is_current"] is False
    assert second_page["has_more"] is False


def test_history_batches_publication_versions(history_repository):
    repository, tenant_id, _, _, _ = history_repository
    engine = repository._session_factory.kw["bind"]
    publication_reads = []

    def count_publication_reads(connection, cursor, statement, parameters, context, many):
        if (
            statement.lstrip().lower().startswith("select")
            and "knowledge_publications" in statement
        ):
            publication_reads.append(statement)

    event.listen(engine, "before_cursor_execute", count_publication_reads)
    try:
        result = repository.get_history(
            GetHistoryInput(
                project_key="catalog", environment="production", tenant_id=str(tenant_id)
            )
        )
    finally:
        event.remove(engine, "before_cursor_execute", count_publication_reads)

    assert [item["publication_version"] for item in result["snapshots"]] == ["2.0.0", "1.0.0"]
    assert len(publication_reads) == 1


def test_history_diffs_entities_against_previous_revision(history_repository):
    repository, tenant_id, _, first_id, second_id = history_repository

    result = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            snapshot_id=second_id,
            limit=1,
        )
    )

    assert result["previous_snapshot"]["snapshot_id"] == str(first_id)
    assert result["changes"] == {
        "added_entities": ["added"],
        "removed_entities": ["removed"],
        "modified_entities": ["changed"],
    }
    assert result["totals"] == {"added": 1, "removed": 1, "modified": 1}
    assert result["has_more"] is False


def test_history_first_snapshot_compares_with_empty_state(history_repository):
    repository, tenant_id, _, first_id, _ = history_repository

    result = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            snapshot_id=first_id,
        )
    )

    assert result["previous_snapshot"] is None
    assert result["changes"]["added_entities"] == ["changed", "removed"]
    assert result["totals"] == {"added": 2, "removed": 0, "modified": 0}


def test_history_rejects_foreign_tenant_and_snapshot(history_repository):
    repository, tenant_id, other_tenant_id, _, second_id = history_repository

    with pytest.raises(LookupError, match="environment not found"):
        repository.get_history(
            GetHistoryInput(
                project_key="catalog", environment="production", tenant_id=str(other_tenant_id)
            )
        )
    with pytest.raises(LookupError, match="snapshot not found"):
        repository.get_history(
            GetHistoryInput(
                project_key="catalog",
                environment="production",
                tenant_id=str(tenant_id),
                snapshot_id=uuid4(),
                query="authentication",
            )
        )


@pytest.mark.parametrize("query", ["Before", "AFTER", "authentication old", "authentication new"])
def test_history_query_matches_both_sides_of_modified_entity(history_repository, query):
    repository, tenant_id, _, first_id, second_id = history_repository
    result = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            snapshot_id=second_id,
            query=query,
        )
    )
    assert result["changes"] == {
        "added_entities": [],
        "removed_entities": [],
        "modified_entities": ["changed"],
    }
    assert result["totals"] == {"added": 0, "removed": 0, "modified": 1}
    change = result["entity_changes"][0]
    assert change["key"] == "changed"
    assert change["status"] == "modified"
    assert change["before"]["snapshot_id"] == str(first_id)
    assert change["after"]["snapshot_id"] == str(second_id)
    with repository._session_factory() as session:
        for side in ("before", "after"):
            entity = session.get(Entity, UUID(change[side]["occurrence_id"]))
            assert entity.entity_key == "changed"


def test_history_query_filters_revisions_before_paging_and_includes_removals(history_repository):
    repository, tenant_id, _, first_id, second_id = history_repository
    request = dict(project_key="catalog", environment="production", tenant_id=str(tenant_id))
    result = repository.get_history(GetHistoryInput(**request, query="Added", limit=1))
    assert [row["snapshot_id"] for row in result["snapshots"]] == [str(second_id)]
    assert result["total_snapshots"] == 1
    assert result["has_more"] is False
    removed = repository.get_history(
        GetHistoryInput(**request, query="removed", snapshot_id=second_id)
    )
    assert removed["totals"] == {"added": 0, "removed": 1, "modified": 0}
    assert removed["entity_changes"][0]["before"]["snapshot_id"] == str(first_id)
    assert removed["entity_changes"][0]["after"] is None
    for query in ("%", "_", "unknown"):
        page = repository.get_history(GetHistoryInput(**request, query=query))
        assert page["snapshots"] == []
        assert page["total_snapshots"] == 0


def test_history_query_ignores_unchanged_entities(history_repository):
    repository, tenant_id, _, _, second_id = history_repository
    with repository._session_factory() as session:
        previous = session.get(Snapshot, second_id)
        third = Snapshot(
            id=uuid4(),
            tenant_id=tenant_id,
            project_id=previous.project_id,
            environment_id=previous.environment_id,
            revision=3,
            schema_version="1.0",
            payload_hash="third",
            project_key="catalog",
        )
        session.add(third)
        for row in session.query(Entity).filter(Entity.snapshot_id == second_id).all():
            session.add(
                Entity(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=row.project_id,
                    snapshot_id=third.id,
                    entity_key=row.entity_key,
                    entity_type=row.entity_type,
                    name=row.name,
                    metadata_json=row.metadata_json,
                )
            )
        session.get(Environment, previous.environment_id).current_snapshot_id = third.id
        session.commit()
        third_id = third.id
    result = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            query="Added",
            limit=1,
        )
    )
    assert [row["snapshot_id"] for row in result["snapshots"]] == [str(second_id)]
    detail = repository.get_history(
        GetHistoryInput(
            project_key="catalog",
            environment="production",
            tenant_id=str(tenant_id),
            query="Added",
            snapshot_id=third_id,
        )
    )
    assert detail["entity_changes"] == []


def test_history_query_pages_filtered_change_totals(history_repository):
    repository, tenant_id, _, first_id, _ = history_repository
    request = dict(
        project_key="catalog",
        environment="production",
        tenant_id=str(tenant_id),
        snapshot_id=first_id,
        query="e",
        limit=1,
    )
    first = repository.get_history(GetHistoryInput(**request))
    second = repository.get_history(GetHistoryInput(**request, offset=1))
    assert first["totals"] == second["totals"] == {"added": 2, "removed": 0, "modified": 0}
    assert first["changes"]["added_entities"] == ["changed"]
    assert second["changes"]["added_entities"] == ["removed"]
    assert first["has_more"] is True
    assert second["has_more"] is False
    assert first["entity_changes"][0]["before"] is None


def test_history_query_cannot_read_another_environment(history_repository):
    repository, tenant_id, _, _, second_id = history_repository
    with repository._session_factory() as session:
        current = session.get(Snapshot, second_id)
        staging_id, staging_snapshot_id = uuid4(), uuid4()
        session.add(
            Environment(
                id=staging_id,
                tenant_id=tenant_id,
                project_id=current.project_id,
                name="staging",
                type="staging",
            )
        )
        session.add(
            Snapshot(
                id=staging_snapshot_id,
                tenant_id=tenant_id,
                project_id=current.project_id,
                environment_id=staging_id,
                revision=1,
                schema_version="1.0",
                payload_hash="staging",
            )
        )
        session.add(
            Entity(
                id=uuid4(),
                tenant_id=tenant_id,
                project_id=current.project_id,
                snapshot_id=staging_snapshot_id,
                entity_key="staging-only",
                entity_type="service",
                metadata_json={"description": "secret"},
            )
        )
        session.commit()
    request = dict(
        project_key="catalog", environment="production", tenant_id=str(tenant_id), query="secret"
    )
    assert repository.get_history(GetHistoryInput(**request))["snapshots"] == []
    with pytest.raises(LookupError, match="snapshot not found"):
        repository.get_history(GetHistoryInput(**request, snapshot_id=staging_snapshot_id))
