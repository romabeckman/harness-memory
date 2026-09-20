from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord


@dataclass(frozen=True, slots=True)
class AppendResult:
    event_id: UUID
    persisted: bool = True
    duplicate: bool = False


class SecurityAuditRepository(Protocol):
    def append(self, record: SecurityAuditRecord) -> AppendResult: ...
