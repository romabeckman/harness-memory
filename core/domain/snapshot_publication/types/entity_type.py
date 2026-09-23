from enum import Enum


class EntityType(str, Enum):
    PROJECT = "project"
    SYSTEM = "system"
    SERVICE = "service"
    API = "api"
    EVENT = "event"
    LIBRARY = "library"
    TEAM = "team"
    ADR = "adr"
    FEATURE = "feature"
    SPEC = "spec"
    DOCUMENT = "document"
    DOCUMENT_REVISION = "document_revision"
    DOCUMENT_SECTION = "document_section"
    RULE = "rule"
