from typing import Protocol

from core.application.entity_discovery.contracts.tenant_scope import TenantScope

from ..use_cases.find_integration_paths.inbound import FindIntegrationPathsInput
from ..use_cases.find_integration_paths.outbound import FindIntegrationPathsOutput


class IntegrationPathRepository(Protocol):
    def find_paths(
        self, scope: TenantScope, query: FindIntegrationPathsInput
    ) -> FindIntegrationPathsOutput: ...

