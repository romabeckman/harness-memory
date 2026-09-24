from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.application.snapshot_publication.services.payload_hash_calculator import (
    PayloadHashCalculator,
)
from core.application.snapshot_publication.services.snapshot_payload import snapshot_payload
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.domain.snapshot_publication.services.snapshot_builder import SnapshotBuilder
from core.infrastructure.postgres.models import Base, Project
from core.infrastructure.postgres.repositories.snapshot_payload_reader import (
    SnapshotPayloadReader,
)
from core.infrastructure.postgres.repositories.snapshot_persistence_mapper import (
    SnapshotPersistenceMapper,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def test_reader_reconstructs_complete_payload_from_normalized_rows():
    request = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            project={"key": "payments", "name": "Payments", "metadata": {"owner": "team-a"}},
            entities=[
                {
                    "key": "service",
                    "type": "service",
                    "name": "Payments Service",
                    "canonical_key": "shared:payments-service",
                    "metadata": {"content": "x" * 5000},
                },
                {"key": "api", "type": "api", "metadata": {"route": "/payments"}},
            ],
            relations=[
                {
                    "ref": "service-api",
                    "source_entity_key": "service",
                    "type": "provides",
                    "target_entity_key": "api",
                    "provenance": "declared",
                    "metadata": {"priority": 1},
                }
            ],
            evidence=[
                {
                    "source": "catalog.yaml",
                    "excerpt": "Payments service exposes the API.",
                    "relation_ref": "service-api",
                    "metadata": {"line": 12},
                },
                {"source": "notes.md", "metadata": {"section": "overview"}},
            ],
        )
    )
    domain_snapshot = SnapshotBuilder().build(request)
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    project_id = uuid4()
    with Session(engine) as session:
        project = Project(
            id=project_id,
            tenant_id="tenant-a",
            key="payments",
            name="Payments",
            metadata_json={"owner": "team-a"},
        )
        session.add(project)
        session.flush()
        rows = SnapshotPersistenceMapper().map(
            domain_snapshot,
            "tenant-a",
            PayloadHashCalculator().calculate(request),
            project_id,
        )
        session.add(rows.snapshot)
        session.flush()
        session.add_all(rows.entities)
        session.add_all(rows.relations)
        session.add_all(rows.evidence)
        session.flush()

        reconstructed = SnapshotPayloadReader().read(session, rows.snapshot)

    assert reconstructed == snapshot_payload(domain_snapshot)
    assert reconstructed["entities"][0]["metadata"]["content"] == "x" * 5000
    assert reconstructed["entities"][0]["canonical_key"] == "shared:payments-service"
    assert reconstructed["relations"][0]["ref"] == "service-api"
    assert reconstructed["evidence"][0]["relation_ref"] == "service-api"
