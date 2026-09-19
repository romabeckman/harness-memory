from collections.abc import Mapping

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.relationship_context.ports.relationship_query_repository import (
    RelationshipQueryRepository,
)
from core.application.relationship_context.use_cases.get_dependencies.inbound import (
    GetDependenciesInput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class GetDependenciesHandler:
    def __init__(self, repository: RelationshipQueryRepository):
        self._repository = repository

    def execute(
        self,
        request: GetDependenciesInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ):
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        scope = (
            tenant_scope
            if isinstance(tenant_scope, TenantScope)
            else TenantScope(getattr(tenant_scope, "tenant_id", ""))
        )
        input_model = (
            request
            if isinstance(request, GetDependenciesInput)
            else GetDependenciesInput.model_validate(request)
        )
        try:
            return self._repository.load_dependencies(scope, input_model)
        except (EntityContextNotFound, RelationshipQueryFailure):
            raise
        except Exception as error:
            raise RelationshipQueryFailure(str(error)) from None


GetDependencies = GetDependenciesHandler
