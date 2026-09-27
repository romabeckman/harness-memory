from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class CanonicalProjectPair:
    project_a_id: UUID
    project_b_id: UUID

    def __init__(self, project_a_id: UUID, project_b_id: UUID) -> None:
        if project_a_id == project_b_id:
            raise ValueError("cannot link project to itself")
        if project_a_id < project_b_id:
            ordered_a, ordered_b = project_a_id, project_b_id
        else:
            ordered_a, ordered_b = project_b_id, project_a_id
        object.__setattr__(self, "project_a_id", ordered_a)
        object.__setattr__(self, "project_b_id", ordered_b)
