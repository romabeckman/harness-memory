from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class SecurityAuditResult:
    event_id: UUID
    persisted: bool
    duplicate: bool
