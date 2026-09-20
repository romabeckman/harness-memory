from pydantic import ValidationError

from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound
from core.application.mcp_access_surface.errors.resource_query_failure import ResourceQueryFailure
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from .authorization_failure import AuthorizationFailure


class ResourceErrorMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = "INVALID_RESOURCE_CONTRACT", "invalid memory resource contract"
        elif isinstance(error, (MissingTenantContext, AuthorizationFailure)):
            code, message = "RESOURCE_UNAUTHORIZED", "memory resource access is unauthorized"
        elif isinstance(error, (ResourceNotFound, EntityContextNotFound)):
            code, message = "RESOURCE_NOT_FOUND", "memory resource not found"
        elif isinstance(error, (ResourceQueryFailure, RelationshipQueryFailure)):
            code, message = "RESOURCE_READ_FAILED", "memory resource read failed"
        else:
            code, message = "RESOURCE_READ_FAILED", "memory resource read failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
