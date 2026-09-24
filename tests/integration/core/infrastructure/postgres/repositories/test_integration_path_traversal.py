from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.types.integration_path_bounds import IntegrationPathBounds
from core.application.integration_paths.types.path_termination_reason import PathTerminationReason
from core.application.integration_paths.use_cases.find_integration_paths.inbound import (
    FindIntegrationPathsInput,
)
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.infrastructure.postgres.models import Base, Entity, Evidence, Project, Relation, Snapshot
from core.infrastructure.postgres.repositories.integration_path_repository import (
    PostgresIntegrationPathRepository,
)


def _repository():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(session_factory):
    tenant = "tenant-a"
    with session_factory() as session:
        project = Project(tenant_id=tenant, key="payments", name="Payments")
        session.add(project)
        session.flush()
        active = Snapshot(
            tenant_id=tenant,
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            metadata_json={},
        )
        session.add(active)
        session.flush()
        project.active_snapshot_id = active.id
        source = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="a-service",
            entity_type="service",
            name="A",
            metadata_json={"tier": 1},
        )
        middle = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="b-api",
            entity_type="api",
            name="B",
            metadata_json={},
        )
        third = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="c-service",
            entity_type="service",
            name="C",
            metadata_json={},
        )
        team = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="platform-team",
            entity_type="team",
            name="Platform",
            metadata_json={},
        )
        disconnected = Entity(
            id=uuid4(),
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=active.id,
            entity_key="z-disconnected",
            entity_type="service",
            name="Disconnected",
            metadata_json={},
        )
        session.add_all([source, middle, third, team, disconnected])
        session.flush()
        direct = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=source.id,
            target_entity_id=middle.id,
            relation_type=RelationType.CONSUMES.value,
            provenance_kind="declared",
            metadata_json={"route": "direct"},
        )
        third_to_middle = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=third.id,
            target_entity_id=middle.id,
            relation_type=RelationType.PROVIDES.value,
            provenance_kind="inferred",
            metadata_json={},
        )
        ownership = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=source.id,
            target_entity_id=team.id,
            relation_type=RelationType.OWNED_BY.value,
            provenance_kind="manual",
            metadata_json={"role": "primary"},
        )
        inbound_ownership = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=team.id,
            target_entity_id=source.id,
            relation_type=RelationType.OWNED_BY.value,
            provenance_kind="declared",
            metadata_json={},
        )
        non_team_ownership = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=source.id,
            target_entity_id=third.id,
            relation_type=RelationType.OWNED_BY.value,
            provenance_kind="declared",
            metadata_json={},
        )
        structural = Relation(
            id=uuid4(),
            tenant_id=tenant,
            snapshot_id=active.id,
            source_entity_id=source.id,
            target_entity_id=disconnected.id,
            relation_type=RelationType.PART_OF.value,
            provenance_kind="declared",
            metadata_json={},
        )
        session.add_all(
            [
                direct,
                third_to_middle,
                ownership,
                inbound_ownership,
                non_team_ownership,
                structural,
            ]
        )
        session.flush()
        session.add_all(
            [
                Evidence(
                    id=uuid4(),
                    tenant_id=tenant,
                    snapshot_id=active.id,
                    relation_id=direct.id,
                    source="route.yaml",
                    excerpt="direct route",
                    metadata_json={"line": 4},
                ),
                Evidence(
                    id=uuid4(),
                    tenant_id=tenant,
                    snapshot_id=active.id,
                    relation_id=ownership.id,
                    source="owners.yaml",
                    excerpt="primary team",
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
        "source": source.id,
        "middle": middle.id,
        "third": third.id,
        "team": team.id,
        "disconnected": disconnected.id,
        "direct_relation": direct.id,
    }


def _query(source_id, target_id, **bounds):
    return FindIntegrationPathsInput(
        source_entity_id=source_id,
        target_entity_id=target_id,
        bounds=IntegrationPathBounds(**bounds),
    )


def test_repository_returns_shortest_path_with_direction_ownership_and_evidence():
    session_factory = _repository()
    ids = _seed(session_factory)
    result = PostgresIntegrationPathRepository(session_factory).find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["middle"])
    )
    assert result.termination_reason is PathTerminationReason.COMPLETE
    assert result.paths[0].hop_count == 1
    assert result.paths[0].hops[0].source.id == ids["source"]
    assert result.paths[0].hops[0].evidence[0].source == "route.yaml"
    assert [owner.owner.id for owner in result.paths[0].entities[0].owners] == [ids["team"]]
    assert result.paths[0].entities[0].owners[0].evidence[0].source == "owners.yaml"


def test_repository_traverses_across_active_snapshots_by_canonical_identity():
    session_factory = _repository()
    tenant = "tenant-a"
    source_identity = uuid4()
    shared_identity = uuid4()
    target_identity = uuid4()
    with session_factory() as session:
        projects = []
        snapshots = []
        for key in ("payments-a", "payments-b"):
            project = Project(tenant_id=tenant, key=key, name=key)
            session.add(project)
            session.flush()
            snapshot = Snapshot(
                tenant_id=tenant,
                project_id=project.id,
                revision=1,
                schema_version="1.0",
                payload_hash=key[0] * 64,
                metadata_json={},
            )
            session.add(snapshot)
            session.flush()
            project.active_snapshot_id = snapshot.id
            projects.append(project)
            snapshots.append(snapshot)

        source, bridge_a, bridge_b, target = (
            Entity(
                id=uuid4(),
                tenant_id=tenant,
                project_id=projects[project_index].id,
                snapshot_id=snapshots[project_index].id,
                identity_id=identity_id,
                entity_key=key,
                entity_type="service",
                name=key,
                metadata_json={},
            )
            for project_index, identity_id, key in (
                (0, source_identity, "source"),
                (0, shared_identity, "shared-a"),
                (1, shared_identity, "shared-b"),
                (1, target_identity, "target"),
            )
        )
        session.add_all([source, bridge_a, bridge_b, target])
        session.flush()
        session.add_all(
            [
                Relation(
                    tenant_id=tenant,
                    snapshot_id=snapshots[0].id,
                    source_entity_id=source.id,
                    target_entity_id=bridge_a.id,
                    source_identity_id=source_identity,
                    target_identity_id=shared_identity,
                    relation_type=RelationType.CONSUMES.value,
                    provenance_kind="declared",
                    metadata_json={},
                ),
                Relation(
                    tenant_id=tenant,
                    snapshot_id=snapshots[1].id,
                    source_entity_id=bridge_b.id,
                    target_entity_id=target.id,
                    source_identity_id=shared_identity,
                    target_identity_id=target_identity,
                    relation_type=RelationType.PROVIDES.value,
                    provenance_kind="declared",
                    metadata_json={},
                ),
            ]
        )
        session.commit()

    result = PostgresIntegrationPathRepository(session_factory).find_paths(
        TenantScope(tenant), _query(source.id, target.id)
    )

    assert len(result.paths) == 1
    assert result.paths[0].hop_count == 2
    assert result.paths[0].hops[0].source.id == source.id
    assert result.paths[0].hops[-1].target.id == target.id
    assert result.paths[0].entities[1].entity.identity_id == shared_identity


def test_repository_traverses_both_relation_directions_and_excludes_non_integration_edges():
    session_factory = _repository()
    ids = _seed(session_factory)
    repository = PostgresIntegrationPathRepository(session_factory)
    result = repository.find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["third"])
    )
    assert len(result.paths) == 1
    assert [hop.traversal_direction.value for hop in result.paths[0].hops] == [
        "outbound",
        "inbound",
    ]
    disconnected = repository.find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["disconnected"])
    )
    assert disconnected.paths == ()
    assert disconnected.termination_reason is PathTerminationReason.COMPLETE


def test_repository_returns_zero_hop_and_enforces_depth_and_path_limits():
    session_factory = _repository()
    ids = _seed(session_factory)
    repository = PostgresIntegrationPathRepository(session_factory)
    zero_hop = repository.find_paths(TenantScope("tenant-a"), _query(ids["source"], ids["source"]))
    assert len(zero_hop.paths) == 1
    assert zero_hop.paths[0].hop_count == 0
    too_shallow = repository.find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["third"], max_depth=1)
    )
    assert too_shallow.paths == ()
    limited = repository.find_paths(
        TenantScope("tenant-a"), _query(ids["source"], ids["middle"], max_paths=1)
    )
    assert len(limited.paths) <= 1


def test_repository_accepts_stable_endpoint_identities():
    session_factory = _repository()
    ids = _seed(session_factory)
    source_identity = uuid4()
    target_identity = uuid4()
    with session_factory() as session:
        session.get(Entity, ids["source"]).identity_id = source_identity
        session.get(Entity, ids["middle"]).identity_id = target_identity
        session.commit()

    result = PostgresIntegrationPathRepository(session_factory).find_paths(
        TenantScope("tenant-a"), _query(source_identity, target_identity)
    )

    assert len(result.paths) == 1
    assert result.termination_reason is PathTerminationReason.COMPLETE


@pytest.mark.parametrize("entity_key", ["unknown", "foreign"])
def test_repository_hides_unavailable_endpoints(entity_key):
    session_factory = _repository()
    ids = _seed(session_factory)
    endpoint = uuid4() if entity_key == "unknown" else ids["team"]
    with pytest.raises(IntegrationPathEndpointNotFound) as raised:
        PostgresIntegrationPathRepository(session_factory).find_paths(
            TenantScope("tenant-b" if entity_key == "foreign" else "tenant-a"),
            _query(endpoint, ids["source"]),
        )
    assert str(raised.value) == "integration path endpoint not found"
