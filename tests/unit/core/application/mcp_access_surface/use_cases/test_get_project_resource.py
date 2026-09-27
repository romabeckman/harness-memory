from unittest.mock import Mock
from uuid import uuid4

import pytest

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.errors.resource_not_found import ResourceNotFound
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds
from core.application.mcp_access_surface.use_cases.get_project_resource.handler import (
    GetProjectResourceHandler,
)
from core.application.mcp_access_surface.use_cases.get_project_resource.outbound import (
    ProjectResourceOutput,
)
from core.application.relationship_context.contracts.entity_context_item import EntityContextItem
from core.application.relationship_context.contracts.project_context_item import ProjectContextItem
from core.domain.snapshot_publication.types.entity_type import EntityType


def _output():
    return ProjectResourceOutput(
        project=ProjectContextItem(
            key="payments", snapshot_id=uuid4(), revision=2, name="Payments"
        ),
        entities=(EntityContextItem(id=uuid4(), key="payments-api", type=EntityType.API),),
        entities_truncated=False,
    )


def test_project_handler_returns_repository_output_and_fixed_bounds():
    repository = Mock()
    expected = _output()
    repository.load_active_project.return_value = expected
    handler = GetProjectResourceHandler(repository)

    result = handler.execute(ProjectResourceInput(project_key="payments"), TenantScope("tenant-a"))

    assert result is expected
    repository.load_active_project.assert_called_once()
    request, tenant, bounds = repository.load_active_project.call_args.args
    assert request.project_key == "payments"
    assert tenant == TenantScope("tenant-a")
    assert bounds == ResourceReadBounds()


def test_project_handler_propagates_not_found_without_retry():
    repository = Mock()
    repository.load_active_project.side_effect = ResourceNotFound()
    handler = GetProjectResourceHandler(repository)

    with pytest.raises(ResourceNotFound):
        handler.execute(ProjectResourceInput(project_key="missing"), TenantScope("tenant-a"))

    repository.load_active_project.assert_called_once()
