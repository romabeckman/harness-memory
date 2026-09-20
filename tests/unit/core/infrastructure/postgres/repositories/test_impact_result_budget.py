from uuid import uuid4

from core.application.impact_analysis.use_cases.analyze_impact.outbound import AnalyzeImpactOutput
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.integration_paths.contracts.ownership_view import OwnershipView
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
