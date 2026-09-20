from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.snapshot_publication.types.publication_context import PublicationContext
from core.application.snapshot_publication.types.publication_record import PublicationRecord
from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.outbound import (
    PublishProjectSnapshotOutput,
)
from core.domain.snapshot_publication.errors.persistence_failure import PersistenceFailure
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def test_handler_passes_tenant_separately_and_maps_activation():
    store = Mock()
    record = PublicationRecord(
        status="ACTIVATED",
        snapshot_id=uuid4(),
        requested_revision=1,
        stored_revision=1,
        active_snapshot_id=uuid4(),
        payload_hash="a" * 64,
        entity_count=1,
        relation_count=0,
        evidence_count=0,
    )
    store.publish_atomically.return_value = record
    request = PublishProjectSnapshotInput.model_validate(valid_payload())

    result = PublishProjectSnapshotHandler(store).execute(request, PublicationContext("tenant-a"))

    assert result.status == "ACTIVATED"
    assert result.payload_hash == "a" * 64
    assert store.publish_atomically.call_args.args[0] == "tenant-a"
    assert "tenant-a" not in store.publish_atomically.call_args.args[1].__repr__()


def test_handler_returns_already_published_and_skips_store_on_domain_failure():
    store = Mock()
    store.publish_atomically.return_value = PublicationRecord(
        status="ALREADY_PUBLISHED",
        snapshot_id=uuid4(),
        requested_revision=1,
        stored_revision=1,
        active_snapshot_id=uuid4(),
        payload_hash="a" * 64,
        entity_count=1,
        relation_count=0,
        evidence_count=0,
    )
    request = PublishProjectSnapshotInput.model_validate(
        valid_payload(
            relations=[
                {
                    "ref": "r",
                    "source_entity_key": "missing",
                    "type": "provides",
                    "target_entity_key": "x",
                    "provenance": "declared",
                }
            ]
        )
    )

    with pytest.raises(Exception):
        PublishProjectSnapshotHandler(store).execute(request, PublicationContext("tenant-a"))
    store.publish_atomically.assert_not_called()


def test_handler_requires_context_and_sanitizes_persistence_failure():
    store = Mock()
    store.publish_atomically.side_effect = PersistenceFailure("INSERT password=secret SQL payload")
    request = PublishProjectSnapshotInput.model_validate(valid_payload())

    with pytest.raises(PersistenceFailure) as error:
        PublishProjectSnapshotHandler(store).execute(request, PublicationContext("tenant-a"))
    assert "secret" not in str(error.value)
    store.publish_atomically.assert_called_once()


def test_publication_output_accepts_only_stable_statuses():
    with pytest.raises(ValidationError):
        PublishProjectSnapshotOutput(
            status="UNKNOWN",
            snapshot_id=uuid4(),
            requested_revision=1,
            stored_revision=1,
            active_snapshot_id=uuid4(),
            payload_hash="a" * 64,
            entity_count=0,
            relation_count=0,
            evidence_count=0,
        )
