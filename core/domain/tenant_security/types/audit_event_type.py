from enum import StrEnum


class AuditEventType(StrEnum):
    PUBLICATION = "publication"
    IMPACT_ANALYSIS = "impact_analysis"
    AUTHENTICATION_FAILURE = "authentication_failure"
    AUTHORIZATION_FAILURE = "authorization_failure"
