from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class User:
    id: UUID
    name: str
    email: str
    tenant_id: UUID | None = None

