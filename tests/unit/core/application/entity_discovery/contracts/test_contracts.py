from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.entity_discovery.contracts.entity_search_criteria import (
    EntitySearchCriteria,
)
from core.application.entity_discovery.contracts.entity_search_item import EntitySearchItem
from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.use_cases.search_entities.inbound import (
    SearchEntitiesInput,
)
from core.domain.snapshot_publication.types.entity_type import EntityType


def test_input_accepts_each_discovery_filter_and_defaults_limit():
    assert SearchEntitiesInput(key=" payments-api ").key == "payments-api"
    assert SearchEntitiesInput(name=" Payments ").name == "Payments"
    assert SearchEntitiesInput(type="api").type is EntityType.API
    assert SearchEntitiesInput(project=" payments ").project == "payments"
    assert SearchEntitiesInput(query=" database ").query == "database"
    assert SearchEntitiesInput(key="x").limit == 100
    assert SearchEntitiesInput(key="x", limit=500).limit == 500


@pytest.mark.parametrize(
    "payload",
    [{"key": "  "}, {"name": "  "}, {"project": "  "}, {"query": "  "}],
)
def test_input_rejects_blank_text_filter(payload):
    with pytest.raises(ValidationError):
        SearchEntitiesInput(**payload)


def test_input_accepts_missing_filters_for_tool_boundary_validation():
    assert SearchEntitiesInput().key is None
    assert SearchEntitiesInput(limit=25).project is None

    with pytest.raises(ValueError, match="at least one discovery filter is required: key, name"):
        EntitySearchCriteria()


@pytest.mark.parametrize("field", ["key", "name", "project", "query"])
def test_input_rejects_text_outside_bounds(field):
    with pytest.raises(ValidationError):
        SearchEntitiesInput(**{field: "x" * 256})


@pytest.mark.parametrize("limit", [0, 501, True, "25", 1.5])
def test_input_rejects_invalid_limit_without_coercion(limit):
    with pytest.raises(ValidationError):
        SearchEntitiesInput(key="x", limit=limit)


def test_input_rejects_unknown_fields_and_unsupported_type():
    with pytest.raises(ValidationError):
        SearchEntitiesInput(key="x", unknown_filter="tenant-a")
    assert SearchEntitiesInput(key="x", tenant_id="tenant-a").tenant_id == "tenant-a"
    with pytest.raises(ValidationError):
        SearchEntitiesInput(type="database")


def test_criteria_normalizes_exact_filters_and_literal_search_terms():
    criteria = EntitySearchCriteria(
        key="Payments-API",
        name="Payments_%",
        type=EntityType.API,
        project="Company/Payments",
        query=" PostgreSQL_% ",
    )

    assert criteria.key == "Payments-API"
    assert criteria.name == "payments_%"
    assert criteria.type is EntityType.API
    assert criteria.project == "Company/Payments"
    assert criteria.name_like == "payments!_!%"
    assert criteria.query_like == "postgresql!_!%"


def test_criteria_escapes_like_markers_without_using_backslash():
    criteria = EntitySearchCriteria(name=r"Rate_%!\X", project=r"Project_%!\X", query=r"DB_%!\X")

    assert criteria.name_like == r"rate!_!%!!\x"
    assert criteria.project == r"Project_%!\X"
    assert criteria.query_like == r"db!_!%!!\x"


def test_search_item_is_bounded_and_page_is_immutable():
    item = EntitySearchItem(
        entity_id=uuid4(),
        key="payments-api",
        name="Payments API",
        type=EntityType.API,
        project_key="payments",
        project_name="Payments",
        snapshot_id=uuid4(),
        revision=2,
    )
    page = EntitySearchPage(items=(item,), limit=1)

    assert set(EntitySearchItem.model_fields) == {
        "entity_id",
        "occurrence_id",
        "tenant_id",
        "project_id",
        "key",
        "name",
        "type",
        "project_key",
        "project_name",
        "snapshot_id",
        "revision",
        "environment_name",
        "is_current_snapshot",
        "publication_id",
        "publication_version",
        "publication_status",
        "deployment_id",
    }
    assert page.count == 1
    with pytest.raises(ValidationError):
        EntitySearchPage(items=(item, item), limit=1)
    with pytest.raises(ValidationError):
        page.items = ()


def test_empty_page_and_tenant_scope_are_valid_immutable_values():
    page = EntitySearchPage(items=(), limit=25)
    scope = TenantScope(" tenant-a ")

    assert page.items == ()
    assert page.next_cursor is None
    assert scope.tenant_id == "tenant-a"
    with pytest.raises(ValueError):
        TenantScope(" ")


def test_entity_search_page_accepts_500_items():
    item = EntitySearchItem(
        entity_id=uuid4(),
        key="payments-api",
        type=EntityType.API,
        project_key="payments",
        snapshot_id=uuid4(),
        revision=1,
    )

    page = EntitySearchPage(items=(item,) * 500, limit=500)

    assert page.count == 500
