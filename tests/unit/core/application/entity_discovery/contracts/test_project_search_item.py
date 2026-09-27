from uuid import uuid4
import pytest
from pydantic import ValidationError

from core.application.entity_discovery.contracts.project_link_item import ProjectLinkItem
from core.application.entity_discovery.contracts.project_search_item import ProjectSearchItem


def test_project_search_item_defaults_links_to_empty_tuple():
    item = ProjectSearchItem(key="order-service", has_active_snapshot=True)

    assert item.links == ()
    assert item.model_dump(mode="json")["links"] == []


def test_project_search_item_retains_links_when_provided():
    link1 = ProjectLinkItem(project_id=uuid4(), name="Auth", tenant_id="tenant-1")
    link2 = ProjectLinkItem(project_id=uuid4(), name="Billing", tenant_id=uuid4())
    item = ProjectSearchItem(
        key="order-service",
        has_active_snapshot=False,
        links=(link1, link2),
    )

    assert len(item.links) == 2
    assert item.links[0] == link1
    assert item.links[1] == link2
    dumped = item.model_dump(mode="json")
    assert len(dumped["links"]) == 2
    assert dumped["links"][0]["name"] == "Auth"


def test_project_search_item_rejects_invalid_link_type():
    with pytest.raises(ValidationError):
        ProjectSearchItem(
            key="order-service",
            has_active_snapshot=False,
            links=("invalid",),  # type: ignore[arg-type]
        )
