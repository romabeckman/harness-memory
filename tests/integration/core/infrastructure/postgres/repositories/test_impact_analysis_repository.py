from os import getenv

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.impact_analysis.types.impact_analysis_bounds import ImpactAnalysisBounds
from core.application.impact_analysis.use_cases.analyze_impact.inbound import (
    AnalyzeImpactInput,
)
from core.application.snapshot_publication.types.publication_context import PublicationContext
from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.infrastructure.postgres.models import (
    Base,
    Entity,
    Evidence,
    Project,
    Relation,
    Snapshot,
    Tenant,
)
from core.infrastructure.postgres.repositories.impact_analysis_repository import (
    PostgresImpactAnalysisRepository,
)
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload

TEST_DATABASE_URL = getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL or not TEST_DATABASE_URL.startswith("postgresql"),
    reason="TEST_DATABASE_URL must point to PostgreSQL for impact repository integration tests",
)


def _session_factory():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(Tenant(id="tenant-a", key="tenant-a", name="Tenant A"))
        session.commit()
    return sessionmaker(bind=engine, expire_on_commit=False)


def _seed(session_factory):
    tenant = "tenant-a"
    with session_factory() as session:
        project = Project(tenant_id=tenant, key="payments", name="Payments")
        session.add(project)
        session.flush()
        snapshot = Snapshot(
            tenant_id=tenant,
            project_id=project.id,
            revision=1,
            schema_version="1.0",
            payload_hash="a" * 64,
            metadata_json={},
        )
        session.add(snapshot)
        session.flush()
        project.active_snapshot_id = snapshot.id
        changed = Entity(
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="payments-api",
            entity_type="api",
            name="Payments API",
            metadata_json={},
        )
        direct = Entity(
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="checkout-service",
            entity_type="service",
            name="Checkout",
            metadata_json={},
        )
        indirect = Entity(
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="billing-service",
            entity_type="service",
            name="Billing",
            metadata_json={},
        )
        team = Entity(
            tenant_id=tenant,
            project_id=project.id,
            snapshot_id=snapshot.id,
            entity_key="payments-team",
            entity_type="team",
            name="Payments Team",
            metadata_json={},
        )
        session.add_all([changed, direct, indirect, team])
        session.flush()
        direct_relation = Relation(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            source_entity_id=direct.id,
            target_entity_id=changed.id,
            relation_type=RelationType.CONSUMES.value,
            provenance_kind="declared",
            metadata_json={"source": "catalog"},
        )
        indirect_relation = Relation(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            source_entity_id=indirect.id,
            target_entity_id=direct.id,
            relation_type=RelationType.DEPENDS_ON.value,
            provenance_kind="observed",
            metadata_json={},
        )
        ownership = Relation(
            tenant_id=tenant,
            snapshot_id=snapshot.id,
            source_entity_id=indirect.id,
            target_entity_id=team.id,
            relation_type=RelationType.OWNED_BY.value,
            provenance_kind="manual",
            metadata_json={},
        )
        session.add_all([direct_relation, indirect_relation, ownership])
        session.flush()
        session.add(
            Evidence(
                tenant_id=tenant,
                snapshot_id=snapshot.id,
                relation_id=direct_relation.id,
                source="catalog.yaml",
                excerpt="checkout consumes payments API",
                metadata_json={},
            )
        )
        session.add(
            Evidence(
                tenant_id=tenant,
                snapshot_id=snapshot.id,
                relation_id=indirect_relation.id,
                source="dependency.yaml",
                excerpt="billing depends on checkout",
                metadata_json={},
            )
        )
        session.commit()
    return {"changed": changed.id, "direct": direct.id, "indirect": indirect.id, "team": team.id}


def test_repository_distinguishes_direct_and_transitive_consumers_with_paths_evidence_and_owners():
    session_factory = _session_factory()
    ids = _seed(session_factory)

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            change_type="contract",
            description="Response changed",
            bounds=ImpactAnalysisBounds(max_depth=4),
        ),
    )

    assert [item.entity.id for item in result.direct_consumers] == [ids["direct"]]
    assert [item.entity.id for item in result.indirect_consumers] == [ids["indirect"]]
    assert [item.id for item in result.affected_teams] == [ids["team"]]
    assert len(result.paths) == 2
    assert result.paths[0].hops[0].evidence[0].source == "catalog.yaml"
    assert result.unknowns == ()


def test_repository_accepts_stable_changed_entity_identity():
    session_factory = _session_factory()
    ids = _seed(session_factory)
    stable_id = __import__("uuid").uuid4()
    with session_factory() as session:
        session.get(Entity, ids["changed"]).identity_id = stable_id
        session.commit()

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"), AnalyzeImpactInput(entity_id=stable_id)
    )

    assert result.changed_entity.identity_id == stable_id


def _publish_cross_project_graph():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(Tenant(id="tenant-a", key="tenant-a", name="Tenant A"))
        session.commit()
    store = PostgresSnapshotPublicationRepository(sessionmaker(bind=engine))
    handler = PublishProjectSnapshotHandler(store)
    context = PublicationContext("tenant-a")
    handler.execute(
        PublishProjectSnapshotInput.model_validate(
            valid_payload(
                project={"key": "catalog", "name": "Catalog", "metadata": {}},
                entities=[
                    {
                        "key": "shared-api",
                        "type": "api",
                        "name": "Shared API",
                        "canonical_key": "shared-api",
                    }
                ],
            )
        ),
        context,
    )
    handler.execute(
        PublishProjectSnapshotInput.model_validate(
            valid_payload(
                project={"key": "checkout", "name": "Checkout", "metadata": {}},
                entities=[
                    {
                        "key": "shared-api",
                        "type": "api",
                        "name": "Shared API",
                        "canonical_key": "shared-api",
                    },
                    {"key": "checkout-service", "type": "service", "name": "Checkout"},
                ],
                relations=[
                    {
                        "ref": "checkout-shared-api",
                        "source_entity_key": "checkout-service",
                        "type": "consumes",
                        "target_entity_key": "shared-api",
                        "provenance": "declared",
                    }
                ],
            )
        ),
        context,
    )
    with sessionmaker(bind=engine)() as session:
        api = session.scalar(
            select(Entity)
            .join(Project, Project.id == Entity.project_id)
            .where(
                Project.key == "catalog",
                Entity.entity_key == "shared-api",
                Entity.snapshot_id == Project.active_snapshot_id,
            )
        )
    return engine, api.id


def test_published_projects_expose_cross_project_direct_impact():
    engine, changed_entity_id = _publish_cross_project_graph()

    result = PostgresImpactAnalysisRepository(sessionmaker(bind=engine)).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(entity_id=changed_entity_id),
    )

    assert [item.entity.key for item in result.direct_consumers] == ["checkout-service"]
    assert [item.key for item in result.affected_projects] == ["checkout"]


def test_published_cross_project_relation_keeps_canonical_endpoint_identity():
    engine, changed_entity_id = _publish_cross_project_graph()

    with sessionmaker(bind=engine)() as session:
        changed = session.get(Entity, changed_entity_id)
        relation = session.scalar(
            select(Relation)
            .join(Snapshot, Snapshot.id == Relation.snapshot_id)
            .join(Project, Project.id == Snapshot.project_id)
            .where(Project.key == "checkout")
        )

    assert relation.target_identity_id == changed.identity_id
    assert relation.target_entity_id != changed.id


def test_max_consumers_bounds_each_graph_query():
    session_factory = _session_factory()
    ids = _seed(session_factory)
    repository = PostgresImpactAnalysisRepository(session_factory)
    original = repository._load_adjacent_relations
    limits = []

    def bounded_loader(session, scope, current_ids, row_limit):
        limits.append(row_limit)
        return original(session, scope, current_ids, row_limit)

    repository._load_adjacent_relations = bounded_loader
    result = repository.analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            bounds=ImpactAnalysisBounds(max_consumers=1),
        ),
    )

    assert result.truncated is True
    assert limits
    assert max(limits) <= 2


def test_evidence_limit_zero_does_not_report_missing_evidence():
    session_factory = _session_factory()
    ids = _seed(session_factory)

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            bounds=ImpactAnalysisBounds(evidence_limit=0),
        ),
    )

    assert result.evidence == ()
    assert result.unknowns == ()


def test_cycle_at_depth_boundary_does_not_mark_result_truncated():
    session_factory = _session_factory()
    ids = _seed(session_factory)
    with session_factory() as session:
        snapshot = session.scalar(select(Snapshot).where(Snapshot.tenant_id == "tenant-a"))
        session.add(
            Relation(
                tenant_id="tenant-a",
                snapshot_id=snapshot.id,
                source_entity_id=ids["direct"],
                target_entity_id=ids["indirect"],
                relation_type=RelationType.DEPENDS_ON.value,
                provenance_kind="observed",
                metadata_json={},
            )
        )
        session.commit()

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            bounds=ImpactAnalysisBounds(max_depth=2),
        ),
    )

    assert result.truncated is False


def test_duplicate_relation_paths_do_not_mark_result_truncated():
    session_factory = _session_factory()
    ids = _seed(session_factory)
    with session_factory() as session:
        snapshot = session.scalar(select(Snapshot).where(Snapshot.tenant_id == "tenant-a"))
        session.add(
            Relation(
                tenant_id="tenant-a",
                snapshot_id=snapshot.id,
                source_entity_id=ids["indirect"],
                target_entity_id=ids["direct"],
                relation_type=RelationType.CONSUMES.value,
                provenance_kind="observed",
                metadata_json={},
            )
        )
        session.commit()

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            bounds=ImpactAnalysisBounds(max_consumers=2),
        ),
    )

    assert [item.entity.id for item in result.indirect_consumers] == [ids["indirect"]]
    assert result.truncated is False


def test_total_result_byte_budget_limits_materialized_evidence():
    session_factory = _session_factory()
    ids = _seed(session_factory)
    with session_factory() as session:
        relation = session.scalar(select(Relation).where(Relation.relation_type == "consumes"))
        session.add_all(
            [
                Evidence(
                    tenant_id="tenant-a",
                    snapshot_id=relation.snapshot_id,
                    relation_id=relation.id,
                    source=f"source-{index}",
                    excerpt="x" * 1024,
                    metadata_json={},
                )
                for index in range(20)
            ]
        )
        session.commit()

    result = PostgresImpactAnalysisRepository(session_factory).analyze_impact(
        TenantScope("tenant-a"),
        AnalyzeImpactInput(
            entity_id=ids["changed"],
            bounds=ImpactAnalysisBounds(
                evidence_limit=20,
                max_result_bytes=64 * 1024,
            ),
        ),
    )

    assert len(result.model_dump_json().encode("utf-8")) <= 64 * 1024
    assert result.truncated is True
    assert len(result.evidence) < 20


def test_same_canonical_consumer_from_two_projects_keeps_both_project_contexts():
    engine = create_engine(TEST_DATABASE_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        session.add(Tenant(id="tenant-a", key="tenant-a", name="Tenant A"))
        session.commit()
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant = "tenant-a"
    changed_identity = __import__("uuid").uuid4()
    consumer_identity = __import__("uuid").uuid4()

    with factory() as session:
        projects = []
        snapshots = []
        for project_key in ("catalog", "checkout", "billing"):
            project = Project(tenant_id=tenant, key=project_key, name=project_key.title())
            session.add(project)
            session.flush()
            snapshot = Snapshot(
                tenant_id=tenant,
                project_id=project.id,
                revision=1,
                schema_version="1.0",
                payload_hash=project_key,
                metadata_json={},
            )
            session.add(snapshot)
            session.flush()
            project.active_snapshot_id = snapshot.id
            projects.append(project)
            snapshots.append(snapshot)

        changed = Entity(
            tenant_id=tenant,
            project_id=projects[0].id,
            snapshot_id=snapshots[0].id,
            identity_id=changed_identity,
            entity_key="shared-api",
            entity_type="api",
            name="Shared API",
            metadata_json={},
        )
        changed_copies = [
            Entity(
                tenant_id=tenant,
                project_id=project.id,
                snapshot_id=snapshot.id,
                identity_id=changed_identity,
                entity_key="shared-api",
                entity_type="api",
                name="Shared API",
                metadata_json={},
            )
            for project, snapshot in zip(projects[1:], snapshots[1:])
        ]
        consumers = [
            Entity(
                tenant_id=tenant,
                project_id=project.id,
                snapshot_id=snapshot.id,
                identity_id=consumer_identity,
                entity_key="worker",
                entity_type="service",
                name="Worker",
                metadata_json={},
            )
            for project, snapshot in zip(projects[1:], snapshots[1:])
        ]
        session.add_all([changed, *changed_copies, *consumers])
        session.flush()
        session.add_all(
            [
                Relation(
                    tenant_id=tenant,
                    snapshot_id=snapshot.id,
                    source_entity_id=consumer.id,
                    target_entity_id=changed_copy.id,
                    source_identity_id=consumer_identity,
                    target_identity_id=changed_identity,
                    relation_type=RelationType.CONSUMES.value,
                    provenance_kind="declared",
                    metadata_json={},
                )
                for consumer, changed_copy, snapshot in zip(
                    consumers, changed_copies, snapshots[1:]
                )
            ]
        )
        session.commit()

    result = PostgresImpactAnalysisRepository(factory).analyze_impact(
        TenantScope(tenant), AnalyzeImpactInput(entity_id=changed.id)
    )

    assert [item.entity.key for item in result.direct_consumers] == ["worker"]
    assert [item.key for item in result.affected_projects] == ["billing", "checkout"]
