from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.integration_paths.errors.integration_path_endpoint_not_found import (
    IntegrationPathEndpointNotFound,
)
from core.application.integration_paths.errors.integration_path_query_failure import (
    IntegrationPathQueryFailure,
)
from core.application.integration_paths.use_cases.find_integration_paths.handler import (
    FindIntegrationPathsHandler,
)
from core.application.integration_paths.use_cases.find_integration_paths.inbound import (
    FindIntegrationPathsInput,
)


def test_input_defaults_and_forbids_tenant_payload():
    request = FindIntegrationPathsInput(source_entity_id=uuid4(), target_entity_id=uuid4())
    assert request.bounds.max_depth == 4
    with pytest.raises(ValidationError):
        FindIntegrationPathsInput(
            source_entity_id=uuid4(), target_entity_id=uuid4(), tenant_id="tenant-b"
        )


@pytest.mark.parametrize("source", ["not-a-uuid"])
def test_input_rejects_malformed_endpoints(source):
    with pytest.raises(ValidationError):
        FindIntegrationPathsInput(source_entity_id=source, target_entity_id=uuid4())


def test_handler_delegates_once_with_validated_input_and_scope():
    repository = Mock()
    expected = object()
    repository.find_paths.return_value = expected
    handler = FindIntegrationPathsHandler(repository)
    request = FindIntegrationPathsInput(source_entity_id=uuid4(), target_entity_id=uuid4())
    scope = TenantScope("tenant-a")
    assert handler.execute(request, scope) is expected
    repository.find_paths.assert_called_once_with(scope, request)


@pytest.mark.parametrize(
    "failure", [IntegrationPathEndpointNotFound(), IntegrationPathQueryFailure()]
)
def test_handler_preserves_typed_failures(failure):
    repository = Mock()
    repository.find_paths.side_effect = failure
    with pytest.raises(type(failure)) as raised:
        FindIntegrationPathsHandler(repository).execute(
            FindIntegrationPathsInput(source_entity_id=uuid4(), target_entity_id=uuid4()),
            TenantScope("tenant-a"),
        )
    assert raised.value is failure


def test_handler_does_not_share_state_between_searches():
    repository = Mock()
    repository.find_paths.side_effect = ["first", "second"]
    handler = FindIntegrationPathsHandler(repository)
    first = FindIntegrationPathsInput(source_entity_id=uuid4(), target_entity_id=uuid4())
    second = FindIntegrationPathsInput(source_entity_id=uuid4(), target_entity_id=uuid4())
    first_scope = TenantScope("tenant-a")
    second_scope = TenantScope("tenant-b")
    assert handler.execute(first, first_scope) == "first"
    assert handler.execute(second, second_scope) == "second"
    assert repository.find_paths.call_args_list[0].args == (first_scope, first)
    assert repository.find_paths.call_args_list[1].args == (second_scope, second)
