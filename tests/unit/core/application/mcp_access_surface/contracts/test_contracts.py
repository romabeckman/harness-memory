from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from core.application.mcp_access_surface.contracts.project_resource_input import (
    ProjectResourceInput,
)
from core.application.mcp_access_surface.contracts.project_resource_output import (
    ProjectResourceOutput,
)
from core.application.mcp_access_surface.contracts.snapshot_context_item import SnapshotContextItem
from core.application.mcp_access_surface.contracts.snapshot_fact_page import SnapshotFactPage
from core.application.mcp_access_surface.contracts.snapshot_resource_input import (
    SnapshotResourceInput,
)
from core.application.mcp_access_surface.contracts.snapshot_resource_output import (
    SnapshotResourceOutput,
)
from core.application.mcp_access_surface.types.resource_read_bounds import ResourceReadBounds


def test_project_resource_input_preserves_valid_decoded_key():
    result = ProjectResourceInput(project_key="github.com/company/payments-api")

    assert result.project_key == "github.com/company/payments-api"


@pytest.mark.parametrize("key", ["", "   ", "x" * 256])
def test_project_resource_input_rejects_blank_or_overlong_key(key):
    with pytest.raises(ValidationError):
        ProjectResourceInput(project_key=key)


def test_project_resource_input_rejects_extra_tenant_field():
    with pytest.raises(ValidationError):
        ProjectResourceInput(project_key="payments", tenant_id="tenant-b")


def test_snapshot_resource_input_parses_uuid():
    snapshot_id = uuid4()

    result = SnapshotResourceInput(snapshot_id=snapshot_id)

    assert result.snapshot_id == snapshot_id
    assert isinstance(result.snapshot_id, UUID)


def test_snapshot_resource_input_rejects_malformed_uuid():
    with pytest.raises(ValidationError):
        SnapshotResourceInput(snapshot_id="not-a-uuid")


def test_resource_read_bounds_are_fixed_and_frozen():
    bounds = ResourceReadBounds()

    assert bounds.fact_limit == 25
    assert bounds.evidence_limit == 5
    with pytest.raises(ValidationError):
        bounds.fact_limit = 10


def test_project_resource_output_rejects_tenant_field():
    with pytest.raises(ValidationError):
        ProjectResourceOutput(
            project={"key": "payments", "snapshot_id": uuid4(), "revision": 1},
            entities=[],
            tenant_id="tenant-a",
        )


def test_snapshot_resource_output_rejects_tenant_field():
    with pytest.raises(ValidationError):
        SnapshotResourceOutput(
            snapshot=SnapshotContextItem(
                id=uuid4(), project_key="payments", revision=1, schema_version="1.0"
            ),
            facts=SnapshotFactPage(),
            tenant_id="tenant-a",
        )
