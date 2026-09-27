from typing import Protocol
from uuid import UUID

from core.domain.project_link.dtos.linked_project_summary import LinkedProjectSummary
from core.domain.project_link.entities.project_link import ProjectLink
from core.domain.project_link.value_objects.canonical_project_pair import CanonicalProjectPair


class ProjectLinkRepository(Protocol):
    def create_link(
        self, pair: CanonicalProjectPair, created_by: UUID | None = None
    ) -> ProjectLink: ...

    def delete_link(self, pair: CanonicalProjectPair) -> bool: ...

    def list_links_for_project(self, project_id: UUID) -> list[LinkedProjectSummary]: ...

    def get_link(self, pair: CanonicalProjectPair) -> ProjectLink | None: ...
