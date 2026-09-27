from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class LinkedProjectSummary:
    project_id: UUID
    key: str
    name: str | None
    tenant_id: UUID
