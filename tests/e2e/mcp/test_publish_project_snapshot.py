import pytest
from fastmcp import Client
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_publish_project_snapshot_is_not_exposed_by_read_only_mcp():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    handler = PublishProjectSnapshotHandler(
        PostgresSnapshotPublicationRepository(sessionmaker(bind=engine))
    )
    server = create_mcp_server(handler=handler, tenant_context=TenantContextProvider("tenant-a"))

    async with Client(server) as client:
        tools = await client.list_tools()
    assert "publish_project_snapshot" not in {tool.name for tool in tools}
