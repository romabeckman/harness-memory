from types import SimpleNamespace
from uuid import uuid4

from core.application.impact_analysis.contracts.impact_consumer_view import ImpactConsumerView
from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.integration_paths.contracts.ownership_view import OwnershipView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.domain.snapshot_publication.types.provenance_kind import ProvenanceKind
from core.domain.snapshot_publication.types.relation_type import RelationType
from core.infrastructure.postgres.repositories.impact_analysis_repository import (
    PostgresImpactAnalysisRepository,
)


def test_result_budget_includes_large_affected_team_metadata():
    output = AnalyzeImpactOutput(
        changed_entity=EntityContextItem(id=uuid4(), key="changed", type="service"),
        affected_teams=tuple(
            EntityContextItem(
                id=uuid4(),
                key=f"team-{index}",
                type="team",
                metadata={"details": "x" * (60 * 1024)},
            )
            for index in range(2)
        ),
    )

    bounded = PostgresImpactAnalysisRepository._fit_result_to_budget(output, 64 * 1024)

    assert bounded.truncated is True
    assert len(bounded.model_dump_json().encode("utf-8")) <= 64 * 1024


def test_affected_team_mapping_has_a_global_cap():
    impacted_id = uuid4()
    owners = tuple(
        OwnershipView(
            relation_id=uuid4(),
            owner=EntityContextItem(id=uuid4(), key=f"team-{index:03}", type="team"),
            provenance="manual",
        )
        for index in range(105)
    )

    teams, truncated = PostgresImpactAnalysisRepository._map_teams(
        {impacted_id: owners}, (impacted_id,)
    )

    assert len(teams) == 100
    assert truncated is True


def test_result_budget_advances_past_fitting_earlier_collection():
    consumer = ImpactConsumerView(
        entity=EntityContextItem(id=uuid4(), key="consumer", type="service"),
        project=ProjectContextItem(
            key="consumer-project", name="Consumer", snapshot_id=uuid4(), revision=1
        ),
        depth=2,
        relation_id=uuid4(),
        relation_type=RelationType.DEPENDS_ON,
        provenance=ProvenanceKind.OBSERVED,
    )
    output = AnalyzeImpactOutput(
        changed_entity=EntityContextItem(id=uuid4(), key="changed", type="service"),
        indirect_consumers=(consumer,),
        affected_projects=tuple(
            ProjectContextItem(
                key=f"project-{index:04}",
                name="Project",
                snapshot_id=uuid4(),
                revision=1,
            )
            for index in range(2000)
        ),
    )

    bounded = PostgresImpactAnalysisRepository._fit_result_to_budget(output, 64 * 1024)

    assert len(bounded.model_dump_json().encode("utf-8")) <= 64 * 1024
    assert bounded.indirect_consumers == ()
    assert bounded.truncated is True


def test_owner_limit_sentinel_is_removed_and_marks_truncation():
    source = SimpleNamespace(id=uuid4(), identity_id=None)
    rows = tuple((object(), source, object(), object(), object()) for _ in range(3))

    bounded, truncated = PostgresImpactAnalysisRepository._trim_owner_rows(rows, 2)

    assert len(bounded) == 2
    assert truncated is True
