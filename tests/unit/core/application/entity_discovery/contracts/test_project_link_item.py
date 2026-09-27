from uuid import UUID, uuid4
import pytest
from pydantic import ValidationError

from core.application.entity_discovery.contracts.project_link_item import ProjectLinkItem


def test_create_project_link_item_successfully():
    proj_id = uuid4()
    tenant_id = uuid4()
    item = ProjectLinkItem(project_id=proj_id, name="Payment Service", tenant_id=tenant_id)

    assert item.project_id == proj_id
    assert item.name == "Payment Service"
    assert item.tenant_id == tenant_id


def test_create_project_link_item_with_string_tenant_and_none_name():
    proj_id = uuid4()
    item = ProjectLinkItem(project_id=proj_id, name=None, tenant_id="tenant-123")

    assert item.project_id == proj_id
    assert item.name is None
    assert item.tenant_id == "tenant-123"


def test_reject_extra_fields():
    proj_id = str(uuid4())
    with pytest.raises(ValidationError):
        ProjectLinkItem.model_validate(
            {
                "project_id": proj_id,
                "name": "Auth Service",
                "tenant_id": "tenant-abc",
                "created_by": str(uuid4()),
            }
        )


def test_reject_missing_or_malformed_project_id():
    with pytest.raises(ValidationError):
        ProjectLinkItem(project_id="invalid-uuid", tenant_id="tenant-123")  # type: ignore[arg-type]

    with pytest.raises(ValidationError):
        ProjectLinkItem.model_validate({"tenant_id": "tenant-123"})


def test_immutability():
    proj_id = uuid4()
    item = ProjectLinkItem(project_id=proj_id, name="Test", tenant_id="tenant-123")
    with pytest.raises(ValidationError):
        item.name = "Other"  # type: ignore[misc]
