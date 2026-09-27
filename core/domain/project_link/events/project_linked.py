from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProjectLinked:
    link_id: UUID
    project_a_id: UUID
    project_b_id: UUID
    created_at: datetime
