from unittest.mock import Mock
from uuid import uuid4

import pytest

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.relationship_context.types.relationship_direction import RelationshipDirection
from core.application.relationship_context.use_cases.get_dependencies.handler import (
    GetDependenciesHandler,
)
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


def test_get_dependencies_delegates_direction_and_bounds_once():
    repository = Mock()
    expected = object()
    repository.load_dependencies.return_value = expected
    request = GetDependenciesInput(
        entity_id=uuid4(), direction=RelationshipDirection.OUTBOUND, limit=7, evidence_limit=1
    )
    scope = TenantScope("tenant-a")

    result = GetDependenciesHandler(repository).execute(request, scope)

    assert result is expected
    repository.load_dependencies.assert_called_once_with(scope, request)


def test_get_dependencies_maps_invalid_trusted_context_to_missing_context():
    repository = Mock()

    with pytest.raises(MissingTenantContext):
        GetDependenciesHandler(repository).execute(
            GetDependenciesInput(entity_id=uuid4()), object()
        )
    repository.load_dependencies.assert_not_called()


@pytest.mark.parametrize("failure", [EntityContextNotFound(), RelationshipQueryFailure()])
def test_get_dependencies_preserves_typed_repository_failures(failure):
    repository = Mock()
    repository.load_dependencies.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        GetDependenciesHandler(repository).execute(
            GetDependenciesInput(entity_id=uuid4()), TenantScope("tenant-a")
        )

    assert raised.value is failure
