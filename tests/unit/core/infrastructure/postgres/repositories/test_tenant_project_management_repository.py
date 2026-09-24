from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.tenant_project_management_repository import (
    PostgresTenantProjectManagementRepository,
)


def _repo():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return PostgresTenantProjectManagementRepository(factory)


def test_list_tenants_and_projects_repository():
    repo = _repo()
    t1 = repo.create_tenant("tenant-1", "Tenant One", {"env": "prod"})
    t2 = repo.create_tenant("tenant-2", "Tenant Two", {})
    repo.update_tenant(t2["id"], {"status": "disabled"})

    # Test list_tenants
    active_tenants = repo.list_tenants(status="active")
    assert active_tenants["total"] == 1
    assert active_tenants["items"][0]["key"] == "tenant-1"

    all_tenants = repo.list_tenants()
    assert all_tenants["total"] == 2

    # Test create_project, get_project, list_projects
    p1 = repo.create_project(t1["id"], "proj-alpha", "Alpha", {"tier": 1})
    p2 = repo.create_project(t1["id"], "proj-beta", "Beta", {})

    found = repo.get_project(t1["id"], "proj-alpha")
    assert found is not None
    assert found["name"] == "Alpha"

    proj_list = repo.list_projects(tenant_id=t1["id"])
    assert proj_list["total"] == 2
    assert {p["key"] for p in proj_list["items"]} == {"proj-alpha", "proj-beta"}
