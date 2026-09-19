from datetime import datetime

import pytest
from pydantic import ValidationError

from core.application.snapshot_publication.contracts.entity_input import EntityInput
from core.application.snapshot_publication.contracts.evidence_input import EvidenceInput
from core.application.snapshot_publication.contracts.project_input import ProjectInput
from core.application.snapshot_publication.contracts.relation_input import RelationInput
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from tests.unit.core.application.snapshot_publication.helpers import valid_payload


def test_inbound_contract_accepts_valid_payload_and_is_immutable():
    request = PublishProjectSnapshotInput.model_validate(valid_payload())

    assert request.project.key == "payments"
    with pytest.raises(ValidationError):
        request.revision = 2
    with pytest.raises(AttributeError):
        request.entities.append(request.entities[0])


@pytest.mark.parametrize("version", ["2.0", 2.0])
def test_inbound_contract_rejects_unsupported_schema_version(version):
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(valid_payload(schema_version=version))


@pytest.mark.parametrize("revision", [True, False, 0, -1, 1.5, "1"])
def test_inbound_contract_rejects_non_positive_integer_revision(revision):
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(valid_payload(revision=revision))


def test_inbound_contract_rejects_naive_generated_at_and_unknown_tenant():
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(
            valid_payload(generated_at=datetime(2026, 9, 17, 12))
        )
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(valid_payload(tenant_id="untrusted"))


@pytest.mark.parametrize(
    "factory",
    [
        lambda: ProjectInput(key="x", unknown=True),
        lambda: EntityInput(key="x", type="service", unknown=True),
        lambda: RelationInput(
            ref="r",
            source_entity_key="x",
            type="provides",
            target_entity_key="x",
            provenance="declared",
            unknown=True,
        ),
        lambda: EvidenceInput(source="source", unknown=True),
    ],
)
def test_component_contracts_reject_unknown_fields(factory):
    with pytest.raises(ValidationError):
        factory()


def test_component_contracts_enforce_evidence_bounds_and_metadata_object():
    with pytest.raises(ValidationError):
        EvidenceInput(source="x" * 1025)
    with pytest.raises(ValidationError):
        EvidenceInput(source="source", excerpt="x" * 4097)
    with pytest.raises(ValidationError):
        EntityInput(key="x", type="service", metadata=[])


def test_inbound_contract_enforces_collection_caps_and_payload_size():
    entities = [{"key": f"service-{index}", "type": "service"} for index in range(10_001)]
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(valid_payload(entities=entities))

    huge = {"value": "x" * (10 * 1024 * 1024)}
    with pytest.raises(ValidationError):
        PublishProjectSnapshotInput.model_validate(
            valid_payload(project={"key": "p", "metadata": huge})
        )
