from core.application.snapshot_publication.services.canonical_payload_serializer import (
    CanonicalPayloadSerializer,
)
from core.application.snapshot_publication.services.payload_hash_calculator import (
    PayloadHashCalculator,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def test_payload_hash_is_canonical_and_excludes_tenant_context():
    first = PublishProjectSnapshotInput.model_validate(valid_payload())
    second = PublishProjectSnapshotInput.model_validate(
        {
            **valid_payload(),
            "generated_at": "2026-09-17T09:00:00-03:00",
            "project": {"metadata": {}, "name": "Payments", "key": "payments"},
        }
    )

    calculator = PayloadHashCalculator(CanonicalPayloadSerializer())
    assert calculator.calculate(first) == calculator.calculate(second)
    assert len(calculator.calculate(first).value) == 64
    assert calculator.calculate(first, tenant_id="tenant-a") == calculator.calculate(
        first, tenant_id="tenant-b"
    )


def test_payload_hash_changes_for_revision_fact_order_and_metadata():
    calculator = PayloadHashCalculator(CanonicalPayloadSerializer())
    first = PublishProjectSnapshotInput.model_validate(valid_payload())
    changed_revision = PublishProjectSnapshotInput.model_validate(valid_payload(revision=2))
    changed_metadata = PublishProjectSnapshotInput.model_validate(
        valid_payload(project={"key": "payments", "metadata": {"owner": "team-a"}})
    )
    assert calculator.calculate(first) != calculator.calculate(changed_revision)
    assert calculator.calculate(first) != calculator.calculate(changed_metadata)


def test_serializer_normalizes_datetime_without_mutating_contract():
    request = PublishProjectSnapshotInput.model_validate(valid_payload())

    serialized = CanonicalPayloadSerializer().serialize(request)

    assert b'"generated_at":"2026-09-17T12:00:00.000000Z"' in serialized
