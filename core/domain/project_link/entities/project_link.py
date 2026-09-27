from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from core.domain.project_link.events.project_linked import ProjectLinked
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


@dataclass
class ProjectLink:
    pair: CanonicalProjectPair
    created_by: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    events: list[Any] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.pair, CanonicalProjectPair):
            raise ValueError("pair must be a CanonicalProjectPair")
        if not self.events:
            self.events.append(
                ProjectLinked(
                    link_id=self.id,
                    project_a_id=self.pair.project_a_id,
                    project_b_id=self.pair.project_b_id,
                    created_at=self.created_at,
                )
            )
