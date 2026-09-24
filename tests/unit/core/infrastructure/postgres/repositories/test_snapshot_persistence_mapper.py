from core.application.snapshot_publication.services.payload_hash_calculator import (
    PayloadHashCalculator,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.domain.snapshot_publication.services.snapshot_builder import SnapshotBuilder
from core.infrastructure.postgres.repositories.snapshot_persistence_mapper import (
    SnapshotPersistenceMapper,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def test_mapper_persists_snapshot_fields_and_resolves_local_fact_references():
    request = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            entities=[
                {"key": "service", "type": "service", "metadata": {"owner": "team-a"}},
                {"key": "api", "type": "api"},
            ],
            relations=[
                {
                    "ref": "service-api",
                    "source_entity_key": "service",
                    "type": "provides",
                    "target_entity_key": "api",
                    "provenance": "declared",
                }
            ],
            evidence=[{"source": "catalog.yaml", "relation_ref": "service-api"}],
        )
    )
    snapshot = SnapshotBuilder().build(request)
    rows = SnapshotPersistenceMapper().map(
        snapshot, "tenant-a", PayloadHashCalculator().calculate(request), __import__("uuid").uuid4()
    )

    assert rows.snapshot.project_key == "payments"
    assert rows.snapshot.project_name == "Payments"
    assert rows.snapshot.generated_at.isoformat().startswith("2026-09-17T12:00:00")
    assert rows.entities[0].metadata_json == {"owner": "team-a"}
    assert rows.entities[0].canonical_key is None
    assert rows.entities[0].graph_position == 0
    assert rows.entities[1].graph_position == 1
    assert rows.relations[0].source_entity_id == rows.entity_ids["service"]
    assert rows.relations[0].target_entity_id == rows.entity_ids["api"]
    assert rows.relations[0].relation_ref == "service-api"
    assert rows.relations[0].graph_position == 0
    assert rows.evidence[0].relation_id == rows.relation_ids["service-api"]
    assert rows.evidence[0].graph_position == 0


def test_mapper_assigns_tenant_scoped_canonical_identity_across_project_snapshots():
    mapper = SnapshotPersistenceMapper()
    first = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            project={"key": "catalog", "name": "Catalog", "metadata": {}},
            entities=[{"key": "shared-api", "type": "api", "canonical_key": "shared-api"}],
        )
    )
    second = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            project={"key": "checkout", "name": "Checkout", "metadata": {}},
            entities=[{"key": "shared-api", "type": "api", "canonical_key": "shared-api"}],
        )
    )
    first_rows = mapper.map(
        SnapshotBuilder().build(first),
        "tenant-a",
        PayloadHashCalculator().calculate(first),
        __import__("uuid").uuid4(),
    )
    second_rows = mapper.map(
        SnapshotBuilder().build(second),
        "tenant-a",
        PayloadHashCalculator().calculate(second),
        __import__("uuid").uuid4(),
    )

    assert first_rows.entities[0].identity_id == second_rows.entities[0].identity_id


def test_mapper_does_not_merge_same_entity_key_across_unrelated_projects():
    mapper = SnapshotPersistenceMapper()
    first = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            project={"key": "catalog", "name": "Catalog", "metadata": {}},
            entities=[{"key": "worker", "type": "service"}],
        )
    )
    second = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            project={"key": "billing", "name": "Billing", "metadata": {}},
            entities=[{"key": "worker", "type": "service"}],
        )
    )

    first_rows = mapper.map(
        SnapshotBuilder().build(first),
        "tenant-a",
        PayloadHashCalculator().calculate(first),
    )
    second_rows = mapper.map(
        SnapshotBuilder().build(second),
        "tenant-a",
        PayloadHashCalculator().calculate(second),
    )

    assert first_rows.entities[0].identity_id != second_rows.entities[0].identity_id
