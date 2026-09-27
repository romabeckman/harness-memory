from pydantic import BaseModel, ConfigDict, StrictBool, StrictStr, model_validator

from core.application.integration_paths.contracts.integration_path_view import IntegrationPathView
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.evidence_view import EvidenceView
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem

from ...contracts.impact_consumer_view import ImpactConsumerView


class AnalyzeImpactOutput(BaseModel):
    changed_entity: EntityContextItem
    direct_consumers: tuple[ImpactConsumerView, ...] = ()
    indirect_consumers: tuple[ImpactConsumerView, ...] = ()
    affected_projects: tuple[ProjectContextItem, ...] = ()
    affected_teams: tuple[EntityContextItem, ...] = ()
    paths: tuple[IntegrationPathView, ...] = ()
    evidence: tuple[EvidenceView, ...] = ()
    unknowns: tuple[StrictStr, ...] = ()
    truncated: StrictBool = False

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_consumer_classifications(self):
        direct_ids = {item.entity.identity_id or item.entity.id for item in self.direct_consumers}
        indirect_ids = {
            item.entity.identity_id or item.entity.id for item in self.indirect_consumers
        }
        overlap = direct_ids & indirect_ids
        if overlap:
            raise ValueError("direct_consumers and indirect_consumers must be disjoint")
        if any(item.depth != 1 for item in self.direct_consumers):
            raise ValueError("direct_consumers must contain depth-one consumers")
        if any(item.depth < 2 for item in self.indirect_consumers):
            raise ValueError("indirect_consumers must contain depth-two-or-greater consumers")
        return self

    @property
    def direct(self) -> tuple[ImpactConsumerView, ...]:
        return self.direct_consumers

    @property
    def indirect(self) -> tuple[ImpactConsumerView, ...]:
        return self.indirect_consumers

    @property
    def dependency_paths(self) -> tuple[IntegrationPathView, ...]:
        return self.paths

    @property
    def projects(self) -> tuple[ProjectContextItem, ...]:
        return self.affected_projects

    @property
    def teams(self) -> tuple[EntityContextItem, ...]:
        return self.affected_teams


ImpactAnalysisOutput = AnalyzeImpactOutput
