from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.types.audit_outcome import AuditOutcome
from core.domain.tenant_security.types.audit_phase import AuditPhase


class SecurityAuditCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, hide_input_in_errors=True)

    request_id: UUID = Field(default_factory=uuid4)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    event_type: AuditEventType
    phase: AuditPhase
    outcome: AuditOutcome
    component_kind: str = Field(min_length=1, max_length=64)
    component_name: str = Field(min_length=1, max_length=255)
    required_scope: str | None = Field(default=None, max_length=64)
    tenant_id: str | None = Field(default=None, max_length=255)
    subject: str | None = Field(default=None, max_length=255)
    reason_code: str | None = Field(default=None, max_length=128)
    safe_details: dict[str, str] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def normalize_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @field_validator(
        "component_kind",
        "component_name",
        "required_scope",
        "tenant_id",
        "subject",
        "reason_code",
    )
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("text value must not be blank")
        return value

    @field_validator("safe_details")
    @classmethod
    def validate_details(cls, value: dict[str, Any]) -> dict[str, str]:
        allowed = {"project_key", "revision", "entity_id", "change_type"}
        if any(key not in allowed for key in value):
            raise ValueError("safe_details contains a non-allowlisted field")
        for key, item in value.items():
            if not isinstance(item, str) or not item.strip() or len(item.strip()) > 255:
                raise ValueError(f"safe_details.{key} is invalid")
        if len(str(value).encode("utf-8")) > 4096:
            raise ValueError("safe_details exceeds maximum size")
        return {key: item.strip() for key, item in value.items()}

    @model_validator(mode="after")
    def validate_event_state(self) -> "SecurityAuditCommand":
        if self.event_type is AuditEventType.AUTHENTICATION_FAILURE:
            if self.phase is not AuditPhase.COMPLETED or self.outcome is not AuditOutcome.DENIED:
                raise ValueError("authentication failure must be completed and denied")
            return self
        if not self.tenant_id or not self.subject:
            raise ValueError("tenant and subject are required for authenticated audit events")
        if self.event_type is AuditEventType.AUTHORIZATION_FAILURE:
            if self.phase is not AuditPhase.COMPLETED or self.outcome is not AuditOutcome.DENIED:
                raise ValueError("authorization failure must be completed and denied")
        elif self.phase is AuditPhase.ATTEMPTED and self.outcome is not AuditOutcome.PENDING:
            raise ValueError("attempted operation must be pending")
        elif self.phase is AuditPhase.COMPLETED and self.outcome not in {
            AuditOutcome.SUCCEEDED,
            AuditOutcome.FAILED,
        }:
            raise ValueError("completed operation must be succeeded or failed")
        return self
