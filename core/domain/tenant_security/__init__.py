"""Domain types for tenant authentication, authorization, and security audit."""

from .entities.security_audit_record import SecurityAuditRecord
from .value_objects.authenticated_principal import AuthenticatedPrincipal

__all__ = ["AuthenticatedPrincipal", "SecurityAuditRecord"]
