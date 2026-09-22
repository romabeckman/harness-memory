from unittest.mock import Mock

import pytest
from fastmcp import Client

from core.application.entity_discovery.contracts.entity_search_page import EntitySearchPage
from core.application.entity_discovery.use_cases.search_entities.handler import (
    SearchEntitiesHandler,
)
from harness_memory_mcp.server.factory import create_mcp_server
from harness_memory_mcp.services.tenant_context import TenantContextProvider


@pytest.mark.asyncio
async def test_search_entities_is_catalogued_beside_publication_when_both_handlers_exist():
    publication = Mock()
    publication.execute.side_effect = RuntimeError("unused")
    search_repository = Mock()
    search_repository.search.return_value = EntitySearchPage(items=(), limit=25)
    server = create_mcp_server(
        handler=publication,
        search_handler=SearchEntitiesHandler(search_repository),
        tenant_context=TenantContextProvider("tenant-a"),
    )

    async with Client(server) as client:
        tools = await client.list_tools()

    assert [tool.name for tool in tools] == ["search_entities"]
