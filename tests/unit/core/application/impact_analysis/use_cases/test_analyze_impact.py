from unittest.mock import Mock
from uuid import uuid4

import pytest

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.impact_analysis.errors.impact_query_failure import ImpactQueryFailure
from core.application.impact_analysis.use_cases.analyze_impact.handler import (
    AnalyzeImpactHandler,
)
from core.application.impact_analysis.use_cases.analyze_impact.inbound import (
    AnalyzeImpactInput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


def test_handler_delegates_structured_change_with_trusted_scope():
    repository = Mock()
    expected = object()
    repository.analyze_impact.return_value = expected
    request = AnalyzeImpactInput(entity_id=uuid4(), description="Contract changed")
    scope = TenantScope("tenant-a")

    assert AnalyzeImpactHandler(repository).execute(request, scope) is expected
    repository.analyze_impact.assert_called_once_with(scope, request)


def test_handler_rejects_missing_tenant_context_before_repository_call():
    repository = Mock()
    request = AnalyzeImpactInput(entity_id=uuid4())

    with pytest.raises(MissingTenantContext, match="trusted tenant context"):
        AnalyzeImpactHandler(repository).execute(request, None)

    repository.analyze_impact.assert_not_called()


def test_handler_rejects_empty_tenant_context_before_repository_call():
    repository = Mock()
    request = AnalyzeImpactInput(entity_id=uuid4())

    with pytest.raises(MissingTenantContext, match="trusted tenant context"):
        AnalyzeImpactHandler(repository).execute(request, type("Context", (), {"tenant_id": ""})())

    repository.analyze_impact.assert_not_called()


def test_handler_preserves_typed_query_failure():
    repository = Mock()
    failure = ImpactQueryFailure()
    repository.analyze_impact.side_effect = failure

    with pytest.raises(ImpactQueryFailure) as raised:
        AnalyzeImpactHandler(repository).execute(
            AnalyzeImpactInput(entity_id=uuid4()), TenantScope("tenant-a")
        )

    assert raised.value is failure
