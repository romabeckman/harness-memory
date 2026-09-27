from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class ProjectUnlinked:
    project_a_id: UUID
    project_b_id: UUID
    unlinked_at: datetime
