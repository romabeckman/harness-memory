from collections.abc import Mapping

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.snapshot_publication.errors.missing_tenant_context import MissingTenantContext

from ...errors.integration_path_endpoint_not_found import IntegrationPathEndpointNotFound
from ...errors.integration_path_query_failure import IntegrationPathQueryFailure
from ...ports.integration_path_repository import IntegrationPathRepository
from .inbound import FindIntegrationPathsInput


class FindIntegrationPathsHandler:
    def __init__(self, repository: IntegrationPathRepository):
        self._repository = repository

    def execute(
        self,
        request: FindIntegrationPathsInput | Mapping[str, object],
        tenant_scope: TenantScope | object | None,
    ):
        if tenant_scope is None:
            raise MissingTenantContext("trusted tenant context is required")
        scope = (
            tenant_scope
            if isinstance(tenant_scope, TenantScope)
            else TenantScope(getattr(tenant_scope, "tenant_id", ""),
                             getattr(tenant_scope, "is_admin", False))
        )
        input_model = (
            request
            if isinstance(request, FindIntegrationPathsInput)
            else FindIntegrationPathsInput.model_validate(request)
        )
        try:
            return self._repository.find_paths(scope, input_model)
        except (IntegrationPathEndpointNotFound, IntegrationPathQueryFailure):
            raise
        except Exception as error:
            raise IntegrationPathQueryFailure(str(error)) from None


FindIntegrationPaths = FindIntegrationPathsHandler

