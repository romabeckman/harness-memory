from uuid import UUID, uuid4
from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.repositories.tenant_project_management_repository import (
    PostgresTenantProjectManagementRepository,
)


def _repository_and_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    return PostgresTenantProjectManagementRepository(factory), factory, engine


def _repo():
    return _repository_and_factory()[0]


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
    p3 = repo.create_project(t2["id"], "proj-global", "Global", {})

    found = repo.get_project(t1["id"], "proj-alpha")
    assert found is not None
    assert found["name"] == "Alpha"
    assert repo.get_project_by_key("proj-global") == p3

    proj_list = repo.list_projects(tenant_id=t1["id"])
    assert proj_list["total"] == 2
    assert {p["key"] for p in proj_list["items"]} == {"proj-alpha", "proj-beta"}


def test_create_project_commits_one_production_environment_atomically():
    repo, factory, _ = _repository_and_factory()
    tenant = repo.create_tenant("tenant-prod", "Tenant Production", {})

    project = repo.create_project(tenant["id"], "catalog", "Catalog", {})

    with factory() as session:
        environments = session.scalars(
            select(Environment).where(Environment.project_id == UUID(project["id"]))
        ).all()
    assert [(environment.name, environment.type) for environment in environments] == [
        ("production", "production")
    ]


def test_create_project_rolls_back_when_production_environment_insert_fails():
    repo, _, engine = _repository_and_factory()
    tenant = repo.create_tenant("tenant-rollback", "Tenant Rollback", {})

    def fail_environment_insert(connection, cursor, statement, parameters, context, many):
        if statement.lower().startswith("insert into environments"):
            raise RuntimeError("production persistence failed")

    event.listen(engine, "before_cursor_execute", fail_environment_insert)
    try:
        with pytest.raises(RuntimeError, match="production persistence failed"):
            repo.create_project(tenant["id"], "catalog", "Catalog", {})
    finally:
        event.remove(engine, "before_cursor_execute", fail_environment_insert)

    assert repo.get_project(tenant["id"], "catalog") is None
