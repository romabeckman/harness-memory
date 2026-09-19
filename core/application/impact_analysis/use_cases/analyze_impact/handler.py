from collections.abc import Mapping

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from ...errors.impact_entity_not_found import ImpactEntityNotFound
from ...errors.impact_query_failure import ImpactQueryFailure
from ...ports.impact_analysis_repository import ImpactAnalysisRepository
from .inbound import AnalyzeImpactInput


class AnalyzeImpactHandler:
    def __init__(self, repository: ImpactAnalysisRepository):
        self._repository = repository

    def execute(
        self,
        request: AnalyzeImpactInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ):
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        if isinstance(tenant_scope, TenantScope):
            scope = tenant_scope
        else:
            try:
                scope = TenantScope(getattr(tenant_scope, "tenant_id", ""))
            except (TypeError, ValueError, AttributeError):
                raise MissingTenantContext("trusted tenant context is required") from None
        input_model = (
            request
            if isinstance(request, AnalyzeImpactInput)
            else AnalyzeImpactInput.model_validate(request)
        )
        try:
            return self._repository.analyze_impact(scope, input_model)
        except (ImpactEntityNotFound, ImpactQueryFailure):
            raise
        except Exception as error:
            raise ImpactQueryFailure(str(error)) from None


AnalyzeImpact = AnalyzeImpactHandler
