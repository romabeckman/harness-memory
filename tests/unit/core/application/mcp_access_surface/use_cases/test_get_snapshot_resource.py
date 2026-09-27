from unittest.mock import Mock
from uuid import uuid4

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.snapshot_context_item import SnapshotContextItem
from core.application.mcp_access_surface.contracts.snapshot_fact_page import SnapshotFactPage
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.application.mcp_access_surface.use_cases.get_snapshot_resource.handler import (
    GetSnapshotResourceHandler,
)
from core.application.mcp_access_surface.use_cases.get_snapshot_resource.outbound import (
    SnapshotResourceOutput,
)


def test_snapshot_handler_returns_tenant_owned_historical_snapshot_and_bounds():
    repository = Mock()
    expected = SnapshotResourceOutput(
        snapshot=SnapshotContextItem(
            id=uuid4(), project_key="payments", revision=1, schema_version="1.0"
        ),
        facts=SnapshotFactPage(),
    )
    repository.load_snapshot.return_value = expected
    handler = GetSnapshotResourceHandler(repository)
    request = SnapshotResourceInput(snapshot_id=uuid4())

    result = handler.execute(request, TenantScope("tenant-a"))

    assert result is expected
    repository.load_snapshot.assert_called_once_with(
        request, TenantScope("tenant-a"), ResourceReadBounds()
    )
