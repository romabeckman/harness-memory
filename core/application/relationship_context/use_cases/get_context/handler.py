from collections.abc import Mapping

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.errors.entity_context_not_found import (
    EntityContextNotFound,
)
from core.application.relationship_context.errors.entity_context_ambiguous import EntityContextAmbiguous
from core.application.relationship_context.errors.relationship_query_failure import (
    RelationshipQueryFailure,
)
from core.application.relationship_context.ports.relationship_query_repository import (
    RelationshipQueryRepository,
)
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext


class GetContextHandler:
    def __init__(self, repository: RelationshipQueryRepository):
        self._repository = repository

    def execute(
        self,
        request: GetContextInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ):
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        if isinstance(tenant_scope, TenantScope):
            scope = tenant_scope
        else:
            try:
                scope = TenantScope(getattr(tenant_scope, "tenant_id", ""),
                                    getattr(tenant_scope, "is_admin", False))
            except (TypeError, ValueError, AttributeError):
                raise MissingTenantContext("trusted tenant context is required") from None
        input_model = (
            request
            if isinstance(request, GetContextInput)
            else GetContextInput.model_validate(request)
        )
        try:
            return self._repository.load_context(scope, input_model)
        except (EntityContextNotFound, EntityContextAmbiguous, RelationshipQueryFailure):
            raise
        except Exception as error:
            raise RelationshipQueryFailure(str(error)) from None


GetContext = GetContextHandler
