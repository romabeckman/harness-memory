from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Any, Mapping
from uuid import UUID, uuid4

from ..types.audit_event_type import AuditEventType
from ..types.audit_outcome import AuditOutcome
from ..types.audit_phase import AuditPhase

_SAFE_DETAIL_KEYS = frozenset({"project_key", "revision", "entity_id", "change_type"})
_MAX_DETAIL_VALUE = 255
_MAX_SERIALIZED_DETAILS = 4096
_OPERATION_EVENTS = frozenset({AuditEventType.PUBLICATION, AuditEventType.IMPACT_ANALYSIS})


def _text(value: Any, field_name: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field_name} is required")
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field_name} is required")
    if len(value) > _MAX_DETAIL_VALUE:
        raise ValueError(f"{field_name} exceeds {_MAX_DETAIL_VALUE} characters")
    return value or None


@dataclass(frozen=True, slots=True)
class SecurityAuditRecord:
    event_id: UUID
    request_id: UUID
    occurred_at: datetime
    event_type: AuditEventType
    phase: AuditPhase
    outcome: AuditOutcome
    component_kind: str
    component_name: str
    required_scope: str | None = None
    tenant_id: str | None = None
    subject: str | None = None
    reason_code: str | None = None
    safe_details: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize values at the domain boundary.  The record is immutable
        # after creation, so persistence adapters can safely retain it.
        try:
            object.__setattr__(self, "event_id", UUID(str(self.event_id)))
            object.__setattr__(self, "request_id", UUID(str(self.request_id)))
        except (TypeError, ValueError, AttributeError) as error:
            raise ValueError("event_id and request_id must be UUID values") from error
        occurred_at = self.occurred_at
        if not isinstance(occurred_at, datetime):
            raise ValueError("occurred_at must be a datetime")
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        occurred_at = occurred_at.astimezone(timezone.utc)
        object.__setattr__(self, "occurred_at", occurred_at)
        object.__setattr__(self, "event_type", AuditEventType(self.event_type))
        object.__setattr__(self, "phase", AuditPhase(self.phase))
        object.__setattr__(self, "outcome", AuditOutcome(self.outcome))
        object.__setattr__(
            self, "component_kind", _text(self.component_kind, "component_kind", required=True)
        )
        object.__setattr__(
            self, "component_name", _text(self.component_name, "component_name", required=True)
        )
        object.__setattr__(self, "required_scope", _text(self.required_scope, "required_scope"))
        object.__setattr__(self, "tenant_id", _text(self.tenant_id, "tenant_id"))
        object.__setattr__(self, "subject", _text(self.subject, "subject"))
        object.__setattr__(self, "reason_code", _text(self.reason_code, "reason_code"))
        if not isinstance(self.safe_details, Mapping):
            raise ValueError("safe_details must be a mapping")
        details = dict(deepcopy(dict(self.safe_details)))
        if any(key not in _SAFE_DETAIL_KEYS for key in details):
            raise ValueError("safe_details contains a non-allowlisted field")
        for key, value in details.items():
            details[key] = _text(value, f"safe_details.{key}", required=True)  # type: ignore[assignment]
        if len(str(details).encode("utf-8")) > _MAX_SERIALIZED_DETAILS:
            raise ValueError("safe_details exceeds maximum size")
        object.__setattr__(self, "safe_details", MappingProxyType(details))
        self._validate_state()

    def _validate_state(self) -> None:
        if self.event_type is AuditEventType.AUTHENTICATION_FAILURE:
            if self.phase is not AuditPhase.COMPLETED or self.outcome is not AuditOutcome.DENIED:
                raise ValueError("authentication failure must be completed and denied")
        else:
            if not self.tenant_id or not self.subject:
                raise ValueError("tenant and subject are required for authenticated audit events")
        if self.event_type is AuditEventType.AUTHORIZATION_FAILURE:
            if self.phase is not AuditPhase.COMPLETED or self.outcome is not AuditOutcome.DENIED:
                raise ValueError("authorization failure must be completed and denied")
        if self.event_type in _OPERATION_EVENTS:
            if self.phase is AuditPhase.ATTEMPTED and self.outcome is not AuditOutcome.PENDING:
                raise ValueError("attempted operation must be pending")
            if self.phase is AuditPhase.COMPLETED and self.outcome not in {
                AuditOutcome.SUCCEEDED,
                AuditOutcome.FAILED,
            }:
                raise ValueError("completed operation must be succeeded or failed")

    @classmethod
    def create(
        cls,
        *,
        request_id: UUID | str,
        event_type: AuditEventType,
        phase: AuditPhase,
        outcome: AuditOutcome,
        component_kind: str,
        component_name: str,
        occurred_at: datetime | None = None,
        event_id: UUID | None = None,
        required_scope: str | None = None,
        tenant_id: str | None = None,
        subject: str | None = None,
        reason_code: str | None = None,
        safe_details: Mapping[str, str] | None = None,
    ) -> "SecurityAuditRecord":
        return cls(
            event_id=event_id or uuid4(),
            request_id=UUID(str(request_id)),
            occurred_at=occurred_at or datetime.now(timezone.utc),
            event_type=event_type,
            phase=phase,
            outcome=outcome,
            component_kind=component_kind,
            component_name=component_name,
            required_scope=required_scope,
            tenant_id=tenant_id,
            subject=subject,
            reason_code=reason_code,
            safe_details=safe_details or {},
        )

    @classmethod
    def from_command(cls, command: Any) -> "SecurityAuditRecord":
        if hasattr(command, "model_dump"):
            command = command.model_dump()
        if not isinstance(command, Mapping):
            raise ValueError("security audit command is required")
        return cls.create(**dict(command))
