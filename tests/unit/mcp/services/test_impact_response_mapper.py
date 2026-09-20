from pydantic import ValidationError

from core.application.impact_analysis.errors.impact_entity_not_found import ImpactEntityNotFound
from core.application.impact_analysis.errors.impact_query_failure import ImpactQueryFailure
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from harness_memory_mcp.services.impact_response_mapper import ImpactResponseMapper


def test_mapper_returns_stable_impact_error_codes():
    mapper = ImpactResponseMapper()

    assert mapper.failure(ImpactEntityNotFound())["error"]["code"] == "IMPACT_ENTITY_NOT_FOUND"
    assert mapper.failure(ImpactQueryFailure())["error"]["code"] == "IMPACT_QUERY_FAILED"
    assert mapper.failure(MissingTenantContext())["error"]["code"] == "MISSING_TENANT_CONTEXT"
    assert mapper.failure(ValidationError.from_exception_data("Input", []))["error"]["code"] == (
        "INVALID_IMPACT_CONTRACT"
    )
