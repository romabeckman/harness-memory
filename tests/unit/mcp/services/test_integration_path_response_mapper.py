from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.errors.integration_path_query_failure import (
    IntegrationPathQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from harness_memory_mcp.services.integration_path_response_mapper import (
    IntegrationPathResponseMapper,
)


def test_mapper_hides_endpoint_and_query_details():
    mapper = IntegrationPathResponseMapper()
    not_found = mapper.failure(IntegrationPathEndpointNotFound("tenant-b", "secret-id"))
    query = mapper.failure(IntegrationPathQueryFailure("postgres://secret", "SELECT secret"))
    assert not_found == {
        "status": "ERROR",
        "error": {
            "code": "INTEGRATION_PATH_ENDPOINT_NOT_FOUND",
            "message": "integration path endpoint not found",
        },
    }
    assert query["error"]["code"] == "INTEGRATION_PATH_QUERY_FAILED"
    assert "secret" not in str(query)


def test_mapper_uses_stable_missing_context_and_invalid_contract_errors():
    mapper = IntegrationPathResponseMapper()
    assert mapper.failure(MissingTenantContext("tenant-a"))["error"]["code"] == (
        "MISSING_TENANT_CONTEXT"
    )
