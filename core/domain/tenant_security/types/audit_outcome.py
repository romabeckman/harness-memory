from enum import StrEnum


class AuditOutcome(StrEnum):
    PENDING = "pending"
    DENIED = "denied"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
