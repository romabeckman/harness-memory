from typing import Protocol

from core.application.entity_discovery.contracts.tenant_scope import TenantScope

from ..use_cases.analyze_impact.inbound import AnalyzeImpactInput
from ..use_cases.analyze_impact.outbound import AnalyzeImpactOutput


class ImpactAnalysisRepository(Protocol):
    def analyze_impact(
        self, scope: TenantScope, query: AnalyzeImpactInput
    ) -> AnalyzeImpactOutput: ...
