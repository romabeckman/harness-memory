from pydantic import ValidationError

from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from .authorization_failure import AuthorizationFailure


class RelationshipResponseMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = "INVALID_RELATIONSHIP_CONTRACT", "invalid relationship query contract"
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, AuthorizationFailure):
            code, message = "RELATIONSHIP_UNAUTHORIZED", "relationship access is unauthorized"
        elif isinstance(error, EntityContextNotFound):
            code, message = "ENTITY_NOT_FOUND", "entity context not found"
        elif isinstance(error, RelationshipQueryFailure):
            code, message = "RELATIONSHIP_QUERY_FAILED", "relationship query failed"
        else:
            code, message = "RELATIONSHIP_QUERY_FAILED", "relationship query failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
