from .api_access_token import ApiAccessToken
from .api_service_account import ApiServiceAccount
from .api_user import ApiUser
from .base import Base
from .entity import Entity
from .evidence import Evidence
from .foundation_id import FoundationId
from .metadata import MetadataObject
from .environment import Environment
from .knowledge_publication import KnowledgePublication
from .project import Project
from .relation import Relation
from .snapshot import Snapshot
from .tenant import Tenant
from .tenant_id import TenantId
from .tenant_uuid import TenantUUID

__all__ = [
    "ApiAccessToken",
    "ApiServiceAccount",
    "ApiUser",
    "Base",
    "Entity",
    "Environment",
    "Evidence",
    "FoundationId",
    "KnowledgePublication",
    "MetadataObject",
    "Project",
    "Relation",
    "Snapshot",
    "Tenant",
    "TenantId",
    "TenantUUID",
    "SecurityAuditEvent",
]


def __getattr__(name: str):
    if name == "SecurityAuditEvent":
        from .security_audit_event import SecurityAuditEvent

        return SecurityAuditEvent
    raise AttributeError(name)
