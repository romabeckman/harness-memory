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
from core.application.relationship_context.use_cases.get_context.handler import GetContextHandler
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput


def test_get_context_delegates_once_with_validated_input_and_scope():
    repository = Mock()
    expected = object()
    repository.load_context.return_value = expected
    handler = GetContextHandler(repository)
    request = GetContextInput(entity_id=uuid4(), limit=10, evidence_limit=2)
    scope = TenantScope("tenant-a")

    result = handler.execute(request, scope)

    assert result is expected
    repository.load_context.assert_called_once_with(scope, request)


@pytest.mark.parametrize("failure", [EntityContextNotFound(), RelationshipQueryFailure()])
def test_get_context_preserves_typed_repository_failures(failure):
    repository = Mock()
    repository.load_context.side_effect = failure

    with pytest.raises(type(failure)) as raised:
        GetContextHandler(repository).execute(GetContextInput(entity_id=uuid4()), TenantScope("a"))

    assert raised.value is failure


def test_get_context_does_not_share_state_between_executions():
    repository = Mock()
    repository.load_context.side_effect = ["first", "second"]
    handler = GetContextHandler(repository)
    first_request = GetContextInput(entity_id=uuid4())
    second_request = GetContextInput(entity_id=uuid4())
    first_scope = TenantScope("tenant-a")
    second_scope = TenantScope("tenant-b")

    assert handler.execute(first_request, first_scope) == "first"
    assert handler.execute(second_request, second_scope) == "second"
    assert repository.load_context.call_args_list[0].args == (first_scope, first_request)
    assert repository.load_context.call_args_list[1].args == (second_scope, second_request)
