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


def test_mapper_preserves_payload_and_resolves_local_fact_references():
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

    assert rows.snapshot.payload["project"]["key"] == "payments"
    assert rows.entities[0].metadata_json == {"owner": "team-a"}
    assert rows.relations[0].source_entity_id == rows.entity_ids["service"]
    assert rows.relations[0].target_entity_id == rows.entity_ids["api"]
    assert rows.evidence[0].relation_id == rows.relation_ids["service-api"]
