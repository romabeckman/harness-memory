from uuid import uuid4

import pytest
from fastmcp import Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.infrastructure.postgres.models import Base, Project, ProjectLinkModel, Tenant
from core.infrastructure.postgres.repositories.knowledge_read_repository import (
    KnowledgeReadRepository,
)
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def _setup_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    return engine, session_factory


def _seed_data(session_factory):
    with session_factory() as session, session.begin():
        t1 = Tenant(id=uuid4(), key="tenant-1", name="Tenant 1", status="active", metadata_json={})
        t2 = Tenant(id=uuid4(), key="tenant-2", name="Tenant 2", status="active", metadata_json={})
        session.add_all([t1, t2])
        session.flush()

        p_alpha = Project(id=uuid4(), tenant_id=t1.id, key="alpha", name="Alpha Service")
        p_beta = Project(id=uuid4(), tenant_id=t1.id, key="beta", name="Beta Service")
        p_gamma = Project(id=uuid4(), tenant_id=t2.id, key="gamma", name="Gamma Service")
        p_isolated = Project(id=uuid4(), tenant_id=t1.id, key="isolated", name="Isolated Service")
        p_hub = Project(id=uuid4(), tenant_id=t1.id, key="hub", name="Hub Service")
        p_spoke1 = Project(id=uuid4(), tenant_id=t1.id, key="spoke-1", name="Spoke 1")
        p_spoke2 = Project(id=uuid4(), tenant_id=t2.id, key="spoke-2", name="Spoke 2")

        session.add_all([p_alpha, p_beta, p_gamma, p_isolated, p_hub, p_spoke1, p_spoke2])
        session.flush()

        # Links for alpha
        link_alpha_beta = ProjectLinkModel(
            id=uuid4(), project_a_id=p_alpha.id, project_b_id=p_beta.id
        )
        link_gamma_alpha = ProjectLinkModel(
            id=uuid4(), project_a_id=p_gamma.id, project_b_id=p_alpha.id
        )

        # Links for hub
        link_hub_1 = ProjectLinkModel(id=uuid4(), project_a_id=p_hub.id, project_b_id=p_spoke1.id)
        link_hub_2 = ProjectLinkModel(id=uuid4(), project_a_id=p_hub.id, project_b_id=p_spoke2.id)

        session.add_all([link_alpha_beta, link_gamma_alpha, link_hub_1, link_hub_2])
        session.flush()

        return t1, t2, p_alpha, p_beta, p_gamma, p_isolated, p_hub, p_spoke1, p_spoke2


@pytest.mark.asyncio
async def test_search_projects_returns_links_for_intra_and_cross_tenant_associations():
    _, session_factory = _setup_db()
    t1, t2, p_alpha, p_beta, p_gamma, _, _, _, _ = _seed_data(session_factory)
    repo = KnowledgeReadRepository(session_factory)
    server = create_mcp_server(
        project_search_repository=repo,
        tenant_context=TenantContextProvider(str(t1.id)),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", {"key": "alpha"})

    assert result.is_error is False
    data = result.data
    assert data["count"] == 1
    item = data["items"][0]
    assert item["key"] == "alpha"
    assert len(item["links"]) == 2

    # Deterministic sort: Beta Service, Gamma Service
    assert item["links"][0] == {
        "project_id": str(p_beta.id),
        "name": "Beta Service",
        "tenant_id": str(t1.id),
    }
    assert item["links"][1] == {
        "project_id": str(p_gamma.id),
        "name": "Gamma Service",
        "tenant_id": str(t2.id),
    }

    # Verify no private internals leaked
    for link in item["links"]:
        assert set(link.keys()) == {"project_id", "name", "tenant_id"}


@pytest.mark.asyncio
async def test_search_projects_returns_empty_links_array_when_no_links():
    _, session_factory = _setup_db()
    t1, _, _, _, _, p_isolated, _, _, _ = _seed_data(session_factory)
    repo = KnowledgeReadRepository(session_factory)
    server = create_mcp_server(
        project_search_repository=repo,
        tenant_context=TenantContextProvider(str(t1.id)),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", {"key": "isolated"})

    assert result.is_error is False
    assert result.data["items"][0]["links"] == []


@pytest.mark.asyncio
async def test_search_projects_returns_all_links_for_multi_linked_project():
    _, session_factory = _setup_db()
    t1, _, _, _, _, _, p_hub, p_spoke1, p_spoke2 = _seed_data(session_factory)
    repo = KnowledgeReadRepository(session_factory)
    server = create_mcp_server(
        project_search_repository=repo,
        tenant_context=TenantContextProvider(str(t1.id)),
    )

    async with Client(server) as client:
        result = await client.call_tool("search_projects", {"key": "hub"})

    assert result.is_error is False
    links = result.data["items"][0]["links"]
    assert len(links) == 2
    linked_ids = {l["project_id"] for l in links}
    assert linked_ids == {str(p_spoke1.id), str(p_spoke2.id)}


@pytest.mark.asyncio
async def test_search_projects_pagination_and_query_filtering():
    _, session_factory = _setup_db()
    t1, _, _, _, _, _, _, _, _ = _seed_data(session_factory)
    repo = KnowledgeReadRepository(session_factory)
    server = create_mcp_server(
        project_search_repository=repo,
        tenant_context=TenantContextProvider(str(t1.id)),
    )

    async with Client(server) as client:
        # Non-existent query
        empty_res = await client.call_tool("search_projects", {"query": "non-existent"})
        assert empty_res.data["items"] == []
        assert empty_res.data["count"] == 0
        assert empty_res.data["has_more"] is False

        # Blank argument error
        blank_res = await client.call_tool("search_projects", {"key": "   "}, raise_on_error=False)
        assert blank_res.data["error"]["code"] == "INVALID_ARGUMENT"

        # Pagination with limit
        paged_res = await client.call_tool("search_projects", {"limit": 2, "offset": 0})
        assert len(paged_res.data["items"]) == 2
        assert paged_res.data["has_more"] is True
        # Verify each returned item contains its full links list
        for item in paged_res.data["items"]:
            assert isinstance(item["links"], list)


@pytest.mark.asyncio
async def test_search_projects_security_authorization():
    _, session_factory = _setup_db()
    t1, _, _, _, _, _, _, _, _ = _seed_data(session_factory)
    repo = KnowledgeReadRepository(session_factory)

    # Server without memory:read scope
    server = create_mcp_server(
        project_search_repository=repo,
        tenant_context=TenantContextProvider(str(t1.id), scopes=["memory:publish"]),
    )

    async with Client(server) as client:
        unauth_res = await client.call_tool("search_projects", {"key": "alpha"})

    assert unauth_res.data["error"]["code"] == "READ_UNAUTHORIZED"
