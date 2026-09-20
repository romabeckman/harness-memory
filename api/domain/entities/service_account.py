from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class ServiceAccount:
    id: UUID
    tenant_id: UUID
    name: str
