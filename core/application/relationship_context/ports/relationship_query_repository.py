from typing import Protocol

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from core.application.relationship_context.use_cases.get_context.outbound import GetContextOutput
from core.application.relationship_context.use_cases.get_context.page import GetContextPage
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.application.relationship_context.use_cases.get_dependencies.outbound import (
    GetDependenciesOutput,
)


class RelationshipQueryRepository(Protocol):
    def load_context(self, scope: TenantScope, query: GetContextInput) -> GetContextOutput: ...

    def list_contexts(self, scope: TenantScope, query: GetContextInput) -> GetContextPage: ...

    def load_dependencies(
        self, scope: TenantScope, query: GetDependenciesInput
    ) -> GetDependenciesOutput: ...
