from pydantic import ValidationError

from core.application.impact_analysis.errors.impact_entity_not_found import ImpactEntityNotFound
from core.application.impact_analysis.errors.impact_query_failure import ImpactQueryFailure
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from .audited_operation import AuditPersistenceFailure
from .authorization_failure import AuthorizationFailure


class ImpactResponseMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code, message = "INVALID_IMPACT_CONTRACT", self._validation_message(error)
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, AuthorizationFailure):
            code, message = "IMPACT_UNAUTHORIZED", "impact analysis authorization required"
        elif isinstance(error, AuditPersistenceFailure):
            code, message = "SECURITY_AUDIT_FAILED", "security audit is unavailable"
        elif isinstance(error, ImpactEntityNotFound):
            code, message = "IMPACT_ENTITY_NOT_FOUND", "impact analysis entity not found"
        elif isinstance(error, ImpactQueryFailure):
            code, message = "IMPACT_QUERY_FAILED", "impact analysis query failed"
        else:
            code, message = "IMPACT_QUERY_FAILED", "impact analysis query failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}

    @staticmethod
    def _validation_message(error: ValidationError) -> str:
        messages = tuple(str(item.get("msg", "")) for item in error.errors())
        if any("change target entity is required" in message for message in messages):
            return "change target entity is required"
        if any("change target entity is ambiguous" in message for message in messages):
            return "change target entity is ambiguous"
        return "invalid impact analysis contract"
