from .base import Base
from .entity import Entity
from .evidence import Evidence
from .foundation_id import FoundationId
from .metadata import MetadataObject
from .project import Project
from .relation import Relation
from .snapshot import Snapshot

__all__ = [
    "Base",
    "Entity",
    "Evidence",
    "FoundationId",
    "MetadataObject",
    "Project",
    "Relation",
    "Snapshot",
    "SecurityAuditEvent",
]


def __getattr__(name: str):
    if name == "SecurityAuditEvent":
        from .security_audit_event import SecurityAuditEvent

        return SecurityAuditEvent
    raise AttributeError(name)
