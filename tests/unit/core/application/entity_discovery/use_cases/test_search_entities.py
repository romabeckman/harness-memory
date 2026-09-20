from unittest.mock import Mock
from uuid import uuid4

import pytest

from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.use_cases.search_entities.handler import (
    SearchEntities,
    SearchEntitiesHandler,
)
from core.application.entity_discovery.use_cases.search_entities.inbound import SearchEntitiesInput
from core.application.entity_discovery.value_objects.search_cursor import SearchCursor
from core.domain.snapshot_publication.types.entity_type import EntityType


def _item():
    return EntitySearchItem(
        entity_id=uuid4(),
        key="payments-api",
        name="Payments API",
        type=EntityType.API,
        project_key="payments",
        project_name="Payments",
        snapshot_id=uuid4(),
        revision=2,
    )


def test_handler_searches_once_with_normalized_criteria_and_scope():
    repository = Mock()
    repository.search.return_value = EntitySearchPage(items=(_item(),), limit=25)
    handler = SearchEntitiesHandler(repository)

    output = handler.execute(SearchEntitiesInput(name=" Payments "), TenantScope("tenant-a"))

    assert output.count == 1
    assert output.limit == 25
    assert output.items[0].key == "payments-api"
    repository.search.assert_called_once()
    scope, criteria, cursor, limit = repository.search.call_args.args
    assert scope.tenant_id == "tenant-a"
    assert criteria.name == "payments"
    assert cursor is None
    assert limit == 25


def test_handler_maps_empty_and_populated_pages():
    repository = Mock()
    item = _item()
    cursor = SearchCursor(
        version=1,
        filter_fingerprint="a" * 64,
        last_key=item.key,
        last_id=item.entity_id,
    )
    repository.search.side_effect = [
        EntitySearchPage(items=(), limit=25),
        EntitySearchPage(items=(item,), next_cursor=cursor, limit=25),
    ]
    handler = SearchEntities(repository)

    empty = handler.execute(SearchEntitiesInput(key="none"), TenantScope("tenant-a"))
    populated = handler.execute(SearchEntitiesInput(key="payments-api"), TenantScope("tenant-a"))

    assert empty.items == () and empty.count == 0 and empty.next_cursor is None
    assert empty.limit == 25
    assert populated.items == (item,) and populated.count == 1
    assert populated.limit == 25
    assert populated.next_cursor


def test_handler_rejects_missing_scope_and_does_not_query():
    repository = Mock()

    with pytest.raises(RuntimeError, match="tenant context"):
        SearchEntitiesHandler(repository).execute(SearchEntitiesInput(key="payments"), None)

    repository.search.assert_not_called()


def test_handler_sanitizes_repository_failures():
    repository = Mock()
    repository.search.side_effect = RuntimeError(
        "SELECT password=secret tenant-a from /internal/database.py"
    )

    with pytest.raises(RuntimeError) as error:
        SearchEntitiesHandler(repository).execute(
            SearchEntitiesInput(key="payments"), TenantScope("tenant-a")
        )

    assert str(error.value) == "entity search failed"
    assert "secret" not in str(error.value)
