from pydantic import ValidationError

from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.errors.integration_path_query_failure import (
    IntegrationPathQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class IntegrationPathResponseMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = (
                "INVALID_INTEGRATION_PATH_CONTRACT",
                "invalid integration path contract",
            )
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, IntegrationPathEndpointNotFound):
            code, message = (
                "INTEGRATION_PATH_ENDPOINT_NOT_FOUND",
                "integration path endpoint not found",
            )
        elif isinstance(error, IntegrationPathQueryFailure):
            code, message = "INTEGRATION_PATH_QUERY_FAILED", "integration path query failed"
        else:
            code, message = "INTEGRATION_PATH_QUERY_FAILED", "integration path query failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
