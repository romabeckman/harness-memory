from collections.abc import Mapping

from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.search_failure import EntitySearchFailure
from core.application.entity_discovery.ports.entity_search_repository import EntitySearchRepository
from core.application.entity_discovery.services.search_criteria_normalizer import (
    NormalizeEntitySearch,
)
from core.application.entity_discovery.services.search_cursor_codec import SearchCursorCodec
from core.application.entity_discovery.use_cases.search_entities.inbound import SearchEntitiesInput
from core.application.entity_discovery.use_cases.search_entities.outbound import (
    SearchEntitiesOutput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class SearchEntitiesHandler:
    def __init__(
        self,
        repository: EntitySearchRepository,
        normalizer: NormalizeEntitySearch | None = None,
        cursor_codec: SearchCursorCodec | None = None,
    ):
        self._repository = repository
        self._normalizer = normalizer or NormalizeEntitySearch()
        self._cursor_codec = cursor_codec or SearchCursorCodec()

    def execute(
        self,
        request: SearchEntitiesInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ) -> SearchEntitiesOutput:
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        scope = (
            tenant_scope
            if isinstance(tenant_scope, TenantScope)
            else TenantScope(getattr(tenant_scope, "tenant_id", ""))
        )
        input_model = (
            request
            if isinstance(request, SearchEntitiesInput)
            else SearchEntitiesInput.model_validate(request)
        )
        criteria = self._normalizer.execute(input_model)
        cursor = (
            self._cursor_codec.decode(input_model.cursor, criteria)
            if input_model.cursor is not None
            else None
        )
        try:
            page = self._repository.search(scope, criteria, cursor, input_model.limit)
        except EntitySearchFailure:
            raise
        except Exception as error:
            raise EntitySearchFailure(str(error)) from None
        if not isinstance(page, EntitySearchPage):
            raise EntitySearchFailure()
        next_cursor = (
            self._cursor_codec.encode(criteria, page.items[-1])
            if page.next_cursor is not None and page.items
            else None
        )
        return SearchEntitiesOutput(
            items=page.items,
            count=page.count,
            limit=page.limit,
            next_cursor=next_cursor,
        )


SearchEntities = SearchEntitiesHandler
