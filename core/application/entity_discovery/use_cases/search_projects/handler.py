from collections.abc import Mapping

from core.application.entity_discovery.contracts.project_search_page import ProjectSearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.project_search_failure import ProjectSearchFailure
from core.application.entity_discovery.ports.project_search_repository import (
    ProjectSearchRepository,
)
from core.application.entity_discovery.use_cases.search_projects.inbound import (
    SearchProjectsInput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import (
    MissingTenantContext,
)


class SearchProjectsHandler:
    def __init__(self, repository: ProjectSearchRepository) -> None:
        self._repository = repository

    def execute(
        self,
        request: SearchProjectsInput | Mapping[str, object],
        scope: TenantScope | None,
    ) -> ProjectSearchPage:
        query = (
            request
            if isinstance(request, SearchProjectsInput)
            else SearchProjectsInput.model_validate(request)
        )
        if scope is None:
            raise MissingTenantContext("trusted tenant context is required")

        try:
            rows = self._repository.search_projects(
                scope,
                key=query.key,
                query=query.query,
                limit=query.limit + 1,
                offset=query.offset,
            )
            items = tuple(rows[: query.limit])
            return ProjectSearchPage(
                items=items,
                count=len(items),
                limit=query.limit,
                offset=query.offset,
                has_more=len(rows) > query.limit,
            )
        except ProjectSearchFailure:
            raise
        except Exception:
            raise ProjectSearchFailure() from None
