from collections.abc import Callable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.adapters.http.schemas.knowledge_publication_request import (
    KnowledgePublicationRequest,
)
from api.adapters.http.schemas.knowledge_publication_response import (
    KnowledgePublicationResponse,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.inbound import (
    PublishKnowledgeInput,
)
from core.domain.knowledge_publication.types.publication_status import PublicationStatus
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def create_knowledge_publication_router(
    handler, authenticate, baseline_handler=None, authenticate_reader=None,
    tenant_exists: Callable[[str], bool] | None = None,
) -> APIRouter:
    router = APIRouter(tags=["knowledge-publications"])

    @router.get("/knowledge-publications/latest")
    def latest_graph(project_key: str, environment: str, tenant_id: UUID | None = None,
        principal: AuthenticatedPrincipal = Depends(authenticate_reader or authenticate)):
        if baseline_handler is None:
            raise HTTPException(status_code=503, detail="baseline reader unavailable")
        try:
            target_tenant = str(tenant_id) if tenant_id is not None else None
            return baseline_handler.execute(project_key, environment, target_tenant)
        except LookupError as error:
            raise HTTPException(status_code=404, detail="publication baseline not found") from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @router.post(
        "/knowledge-publications",
        response_model=KnowledgePublicationResponse,
    )
    def publish_knowledge(
        request: KnowledgePublicationRequest,
        response: Response,
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ) -> KnowledgePublicationResponse:
        if principal.is_admin:
            if request.tenant_id is None:
                raise HTTPException(status_code=400, detail="tenant_id is required for publication")
        target_tenant = (
            str(request.tenant_id) if request.tenant_id is not None else principal.tenant_id
        )
        if tenant_exists is not None and not tenant_exists(target_tenant):
            raise HTTPException(status_code=404, detail="target tenant not found")
        domain_input = PublishKnowledgeInput(
            tenant_id=target_tenant,
            project_key=request.project_key,
            environment_name=request.environment,
            deployment_id=request.deployment_id,
            version=request.version,
            expected_current_snapshot_id=request.expected_current_snapshot_id,
            metadata=request.metadata,
            entities=tuple(request.entities),
            relations=tuple(request.relations),
            evidence=tuple(request.evidence),
        )
        try:
            output = handler.execute(domain_input)
        except RevisionConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

        if output.status == PublicationStatus.ALREADY_PUBLISHED:
            response.status_code = status.HTTP_200_OK
            status_text = "ALREADY_PUBLISHED"
        else:
            response.status_code = status.HTTP_201_CREATED
            status_text = "ACTIVATED"

        return KnowledgePublicationResponse(
            status=status_text,
            publication_id=output.publication_id,
            snapshot_id=output.snapshot_id,
        )

    return router
