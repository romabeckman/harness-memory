from core.application.tenant_security.ports.security_audit_repository import SecurityAuditRepository
from core.domain.tenant_security.entities.security_audit_record import SecurityAuditRecord

from .inbound import SecurityAuditCommand
from .outbound import SecurityAuditResult


class RecordSecurityAuditHandler:
    def __init__(self, repository: SecurityAuditRepository):
        self._repository = repository

    def execute(self, command: SecurityAuditCommand) -> SecurityAuditResult:
        if not isinstance(command, SecurityAuditCommand):
            command = SecurityAuditCommand.model_validate(command)
        record = SecurityAuditRecord.create(**command.model_dump())
        result = self._repository.append(record)
        return SecurityAuditResult(
            event_id=result.event_id,
            persisted=bool(result.persisted),
            duplicate=bool(result.duplicate),
        )
