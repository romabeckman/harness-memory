from __future__ import annotations

import logging
import re
from collections.abc import Callable, Mapping
from uuid import UUID, uuid4

from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.application.tenant_security.use_cases.record_security_audit.inbound import (
    SecurityAuditCommand,
)
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.types.audit_outcome import AuditOutcome
from core.domain.tenant_security.types.audit_phase import AuditPhase
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal
from .trace_context_holder import TraceContextHolder

logger = logging.getLogger(__name__)


class AuditPersistenceFailure(RuntimeError):
    """Protected operation cannot proceed or safely report completion."""


class ExecuteAuditedOperation:
    def __init__(self, audit_handler: RecordSecurityAuditHandler):
        self._audit_handler = audit_handler

    def execute(
        self,
        *,
        operation: Callable[[], object],
        principal: AuthenticatedPrincipal,
        request_id: UUID | str | None,
        event_type: AuditEventType,
        component: str,
        required_scope: str,
        safe_details: Mapping[str, str] | None = None,
    ) -> object:
        correlation_id = UUID(str(request_id)) if request_id else uuid4()
        details = dict(safe_details or {})
        current_trace_id = TraceContextHolder.get_current_trace_id()
        if current_trace_id and "trace_id" not in details:
            details["trace_id"] = current_trace_id
        current_span_id = TraceContextHolder.get_current_span_id()
        if current_span_id and "span_id" not in details:
            details["span_id"] = current_span_id
        attempted = SecurityAuditCommand(
            request_id=correlation_id,
            event_type=event_type,
            phase=AuditPhase.ATTEMPTED,
            outcome=AuditOutcome.PENDING,
            component_kind="tool",
            component_name=component,
            required_scope=required_scope,
            tenant_id=principal.tenant_id,
            subject=principal.subject,
            safe_details=details,
        )
        try:
            self._audit_handler.execute(attempted)
        except Exception as error:
            logger.error("security audit persistence failed before protected operation")
            raise AuditPersistenceFailure("security audit persistence unavailable") from error
        try:
            result = operation()
        except Exception as error:
            try:
                self._complete(
                    correlation_id,
                    event_type,
                    component,
                    required_scope,
                    principal,
                    AuditOutcome.FAILED,
                    reason_code=self._failure_reason_code(error),
                    safe_details=attempted.safe_details,
                )
            except AuditPersistenceFailure:
                logger.error("security audit completion failed after protected operation")
            raise
        self._complete(
            correlation_id,
            event_type,
            component,
            required_scope,
            principal,
            AuditOutcome.SUCCEEDED,
            safe_details=attempted.safe_details,
        )
        return result

    def _complete(
        self,
        request_id: UUID,
        event_type: AuditEventType,
        component: str,
        required_scope: str,
        principal: AuthenticatedPrincipal,
        outcome: AuditOutcome,
        reason_code: str | None = None,
        safe_details: Mapping[str, str] | None = None,
    ) -> None:
        try:
            self._audit_handler.execute(
                SecurityAuditCommand(
                    request_id=request_id,
                    event_type=event_type,
                    phase=AuditPhase.COMPLETED,
                    outcome=outcome,
                    component_kind="tool",
                    component_name=component,
                    required_scope=required_scope,
                    tenant_id=principal.tenant_id,
                    subject=principal.subject,
                    reason_code=reason_code,
                    safe_details=dict(safe_details or {}),
                )
            )
        except Exception as error:
            logger.error("security audit persistence failed after protected operation")
            raise AuditPersistenceFailure("security audit completion unavailable") from error

    @staticmethod
    def _failure_reason_code(error: Exception) -> str:
        reason = re.sub(r"(?<!^)(?=[A-Z])", "_", type(error).__name__).lower()
        reason = re.sub(r"[^a-z0-9_]+", "_", reason).strip("_")
        return (reason or "operation_failed")[:64]
