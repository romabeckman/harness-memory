from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.infrastructure.postgres.models import Base, Entity, Evidence, Project, Relation, Snapshot
from core.infrastructure.postgres.repositories.relationship_query_repository import (
    PostgresRelationshipQueryRepository,
)


def _repository():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine, sessionmaker(bind=engine, expire_on_commit=False)


def _seed(session_factory):
    tenant = "tenant-a"
    with session_factory() as session:
        project = Project(tenant_id=tenant, key="payments", name="Payments")
        session.add(project)
        session.flush()
        old = Snapshot(
            tenant_id=tenant,
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="1" * 64,
            payload={},
            metadata_json={},
        )
        active = Snapshot(
            tenant_id=tenant,
            project_id=project.id,
            revision=2,
            schema_version="1.0",
            payload_hash="2" * 64,
            payload={},
            metadata_json={},
        )
        other_project = Project(tenant_id="tenant-b", key="payments", name="Other")
        session.add_all([old, active, other_project])
        session.flush()
        project.active_snapshot_id = active.id
        other_snapshot = Snapshot(
            tenant_id="tenant-b",
            project_id=other_project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="3" * 64,
            payload={},
            metadata_json={},
        )
        session.add(other_snapshot)
        session.flush()
        other_project.active_snapshot_id = other_snapshot.id

        service = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="payments-service",
            entity_type="service",
            name="Payments Service",
            metadata_json={"tier": 1},
        )
        api = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="payments-api",
            entity_type="api",
            name="Payments API",
            metadata_json={},
        )
        team = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="payments-team",
            entity_type="team",
            name="Payments Team",
            metadata_json={},
        )
        consumer = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="consumer-service",
            entity_type="service",
            name="Consumer",
            metadata_json={},
        )
        old_entity = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=old.id,
            entity_key="old-service",
            entity_type="service",
            name="Old",
            metadata_json={},
        )
        foreign = Entity(
            id=uuid4(),
            tenant_id="tenant-b",
            project_id=other_project.id,
            snapshot_id=other_snapshot.id,
            entity_key="payments-service",
            entity_type="service",
            name="Foreign",
            metadata_json={},
        )
        session.add_all([service, api, team, consumer, old_entity, foreign])
        session.flush()

        owned = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=service.id,
            target_entity_id=team.id,
            relation_type="owned_by",
            provenance_kind="declared",
            metadata_json={"source": "catalog"},
        )
        dependency = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=service.id,
            target_entity_id=api.id,
            relation_type="depends_on",
            provenance_kind="observed",
            metadata_json={},
        )
        provides = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=service.id,
            target_entity_id=api.id,
            relation_type="provides",
            provenance_kind="declared",
            metadata_json={},
        )
        inbound = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=consumer.id,
            target_entity_id=service.id,
            relation_type="consumes",
            provenance_kind="inferred",
            metadata_json={},
        )
        self_relation = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=service.id,
            target_entity_id=service.id,
            relation_type="subscribes_to",
            provenance_kind="manual",
            metadata_json={},
        )
        old_relation = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=old.id,
            source_entity_id=old_entity.id,
            target_entity_id=old_entity.id,
            relation_type="depends_on",
            provenance_kind="declared",
            metadata_json={},
        )
        session.add_all([owned, dependency, provides, inbound, self_relation, old_relation])
        session.flush()
        session.add_all(
            [
                Evidence(
                    id=uuid4(),
                    tenant_id=tenant,
                    snapshot_id=active.id,
                    relation_id=dependency.id,
                    source="dependency.yaml",
                    excerpt="depends",
                    metadata_json={"line": 1},
                ),
                Evidence(
                    id=uuid4(),
                    tenant_id=tenant,
                    snapshot_id=active.id,
                    relation_id=owned.id,
                    source="owner.yaml",
                    excerpt="owner",
                    metadata_json={},
                ),
                Evidence(
                    id=uuid4(),
                    tenant_id=tenant,
                    snapshot_id=active.id,
                    relation_id=None,
                    source="snapshot.yaml",
                    excerpt="unlinked",
                    metadata_json={},
                ),
            ]
        )
        session.commit()
    return {
        "service": service.id,
        "api": api.id,
        "team": team.id,
        "consumer": consumer.id,
        "old": old_entity.id,
        "foreign": foreign.id,
    }


def test_context_uses_active_snapshot_and_derives_owners_dependencies_and_evidence():
    _, session_factory = _repository()
    ids = _seed(session_factory)

    result = PostgresRelationshipQueryRepository(session_factory).load_context(
        TenantScope("tenant-a"), GetContextInput(entity_id=ids["service"])
    )

    assert result.entity.id == ids["service"]
    assert result.project.revision == 2
    assert [owner.id for owner in result.owners] == [ids["team"]]
    assert {relation.type for relation in result.relations} == {
        RelationType.OWNED_BY,
        RelationType.DEPENDS_ON,
        RelationType.PROVIDES,
        RelationType.CONSUMES,
        RelationType.SUBSCRIBES_TO,
    }
    assert [item.type for item in result.dependencies] == [
        RelationType.CONSUMES,
        RelationType.DEPENDS_ON,
        RelationType.SUBSCRIBES_TO,
    ]
    dependency = next(item for item in result.relations if item.type is RelationType.DEPENDS_ON)
    assert [item.source for item in dependency.evidence] == ["dependency.yaml"]
    assert all(item.source != "snapshot.yaml" for item in dependency.evidence)


def test_dependencies_filter_direction_without_recursion_or_duplicates():
    _, session_factory = _repository()
    ids = _seed(session_factory)
    repository = PostgresRelationshipQueryRepository(session_factory)

    outbound = repository.load_dependencies(
        TenantScope("tenant-a"),
        GetDependenciesInput(entity_id=ids["service"], direction=RelationshipDirection.OUTBOUND),
    )
    inbound = repository.load_dependencies(
        TenantScope("tenant-a"),
        GetDependenciesInput(entity_id=ids["service"], direction=RelationshipDirection.INBOUND),
    )
    both = repository.load_dependencies(
        TenantScope("tenant-a"),
        GetDependenciesInput(entity_id=ids["service"], direction=RelationshipDirection.BOTH),
    )

    assert {item.type for item in outbound.items} == {
        RelationType.DEPENDS_ON,
        RelationType.SUBSCRIBES_TO,
    }
    assert {item.type for item in inbound.items} == {
        RelationType.CONSUMES,
        RelationType.SUBSCRIBES_TO,
    }
    assert len({item.relation_id for item in both.items}) == len(both.items)
    assert sum(item.peer.id == ids["service"] for item in both.items) == 1


def test_dependency_query_is_bounded_and_reports_truncation():
    _, session_factory = _repository()
    ids = _seed(session_factory)
    with session_factory() as session:
        for index in range(4):
            session.add(
                Relation(
                    tenant_id="tenant-a",
                    snapshot_id=session.scalar(
                        select(Project.active_snapshot_id).where(Project.tenant_id == "tenant-a")
                    ),
                    source_entity_id=ids["service"],
                    target_entity_id=ids["api"],
                    relation_type="consumes",
                    provenance_kind="declared",
                    metadata_json={"index": index},
                )
            )
        session.commit()

    result = PostgresRelationshipQueryRepository(session_factory).load_dependencies(
        TenantScope("tenant-a"),
        GetDependenciesInput(
            entity_id=ids["service"], direction=RelationshipDirection.OUTBOUND, limit=2
        ),
    )

    assert len(result.items) == 2
    assert result.truncated is True


@pytest.mark.parametrize("entity_key", ["old", "foreign"])
def test_context_hides_inactive_and_other_tenant_entities(entity_key):
    _, session_factory = _repository()
    ids = _seed(session_factory)

    with pytest.raises(EntityContextNotFound):
        PostgresRelationshipQueryRepository(session_factory).load_context(
            TenantScope("tenant-a"), GetContextInput(entity_id=ids[entity_key])
        )
