from typing import Protocol

from core.application.entity_discovery.contracts.entity_search_criteria import EntitySearchCriteria
from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor


class EntitySearchRepository(Protocol):
    def search(
        self,
        scope: TenantScope,
        criteria: EntitySearchCriteria,
        cursor: SearchCursor | None,
        limit: int,
    ) -> EntitySearchPage: ...
