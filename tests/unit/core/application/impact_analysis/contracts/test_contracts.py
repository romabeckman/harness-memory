from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.impact_analysis.contracts.change_description import ChangeDescription
from core.application.impact_analysis.contracts.impact_consumer_view import ImpactConsumerView
from core.application.impact_analysis.types.impact_analysis_bounds import ImpactAnalysisBounds
from core.application.impact_analysis.use_cases.analyze_impact.inbound import (
    AnalyzeImpactInput,
)
from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType


def test_structured_change_defaults_and_forbids_tenant_payload():
    entity_id = uuid4()

    request = AnalyzeImpactInput(
        entity_id=entity_id,
        change_type="contract",
        description="API response changes",
    )

    assert request.entity_id == entity_id
    assert request.change_type == "contract"
    assert request.bounds.max_depth == 4
    with pytest.raises(ValidationError):
        AnalyzeImpactInput(entity_id=entity_id, tenant_id="tenant-b")


def test_structured_change_can_be_nested_and_rejects_missing_target():
    entity_id = uuid4()
    request = AnalyzeImpactInput(
        change=ChangeDescription(
            entity_id=entity_id,
            change_type="schema",
            description="Field removed",
        )
    )

    assert request.entity_id == entity_id
    assert request.change_type == "schema"

    with pytest.raises(ValidationError):
        AnalyzeImpactInput(change_type="schema", description="No target")


def test_bounds_reject_unbounded_impact_queries():
    with pytest.raises(ValidationError):
        ImpactAnalysisBounds(max_depth=0)
    with pytest.raises(ValidationError):
        ImpactAnalysisBounds(max_consumers=0)


def test_bounds_include_a_total_result_byte_budget():
    bounds = ImpactAnalysisBounds(max_result_bytes=64 * 1024)

    assert bounds.max_result_bytes == 64 * 1024

    with pytest.raises(ValidationError):
        ImpactAnalysisBounds(max_result_bytes=0)


def test_output_rejects_overlapping_consumer_classifications():
    consumer = _consumer(depth=1)

    with pytest.raises(ValidationError, match="direct_consumers"):
        AnalyzeImpactOutput(
            changed_entity=consumer.entity,
            direct_consumers=(consumer,),
            indirect_consumers=(consumer,),
        )


def test_output_rejects_depth_two_consumer_in_direct_classification():
    with pytest.raises(ValidationError, match="depth"):
        AnalyzeImpactOutput(
            changed_entity=_entity("changed"),
            direct_consumers=(_consumer(depth=2),),
        )


def _entity(key: str) -> EntityContextItem:
    return EntityContextItem(id=uuid4(), key=key, type=EntityType.SERVICE)


def _consumer(depth: int) -> ImpactConsumerView:
    return ImpactConsumerView(
        entity=_entity("consumer"),
        project=ProjectContextItem(
            key="project", name="Project", snapshot_id=uuid4(), revision=1
        ),
        depth=depth,
        relation_id=uuid4(),
        relation_type=RelationType.CONSUMES,
        provenance=ProvenanceKind.DECLARED,
    )
