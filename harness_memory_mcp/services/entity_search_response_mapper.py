from pydantic import ValidationError

from core.application.entity_discovery.errors.cursor_validation import SearchCursorValidationError
from core.application.entity_discovery.errors.search_failure import EntitySearchFailure
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class EntitySearchResponseMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = "INVALID_SEARCH_CONTRACT", "invalid entity search contract"
        elif isinstance(error, SearchCursorValidationError):
            code, message = "INVALID_SEARCH_CURSOR", "invalid entity search cursor"
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, EntitySearchFailure):
            code, message = "SEARCH_FAILED", "entity search failed"
        else:
            code, message = "SEARCH_FAILED", "entity search failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
