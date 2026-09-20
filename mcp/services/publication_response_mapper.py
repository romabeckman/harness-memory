from pydantic import ValidationError

from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext
from core.domain.snapshot_publication.errors.persistence_failure import PersistenceFailure
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.snapshot_publication.errors.snapshot_invariant_violation import (
    SnapshotInvariantViolation,
)
from core.domain.snapshot_publication.errors.stale_revision import StaleRevision

from .audited_operation import AuditPersistenceFailure


class PublicationResponseMapper:
    def success(self, result):
        return result.model_dump(mode="json") if hasattr(result, "model_dump") else result

    def failure(self, error: Exception) -> dict:
        if isinstance(error, ValidationError):
            code = (
                "UNSUPPORTED_SCHEMA_VERSION"
                if "schema_version" in str(error)
                else "INVALID_CONTRACT"
            )
            message = (
                "unsupported schema version"
                if code == "UNSUPPORTED_SCHEMA_VERSION"
                else "invalid snapshot contract"
            )
        elif isinstance(error, MissingTenantContext):
            code, message = "MISSING_TENANT_CONTEXT", "trusted tenant context is required"
        elif isinstance(error, SnapshotInvariantViolation):
            code, message = "DOMAIN_INVARIANT_VIOLATION", "snapshot violates domain invariants"
        elif isinstance(error, RevisionConflict):
            code, message = (
                "REVISION_CONFLICT",
                "snapshot revision conflicts with published content",
            )
        elif isinstance(error, StaleRevision):
            code, message = "STALE_REVISION", "snapshot revision is stale"
        elif isinstance(error, AuditPersistenceFailure):
            code, message = "SECURITY_AUDIT_FAILED", "security audit is unavailable"
        elif isinstance(error, PersistenceFailure):
            code, message = "PERSISTENCE_FAILURE", "snapshot publication failed"
        else:
            code, message = "PUBLICATION_FAILED", "snapshot publication failed"
        return {"status": "ERROR", "error": {"code": code, "message": message}}
