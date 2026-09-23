from typing import Protocol, Sequence

from core.application.entity_discovery.contracts.project_search_item import ProjectSearchItem
from core.application.entity_discovery.contracts.tenant_scope import TenantScope


class ProjectSearchRepository(Protocol):
    def search_projects(
        self,
        scope: TenantScope,
        *,
        key: str | None,
        query: str | None,
        limit: int,
        offset: int,
    ) -> Sequence[ProjectSearchItem]: ...
