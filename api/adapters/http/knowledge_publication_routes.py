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
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal
from core.domain.snapshot_publication.errors.revision_conflict import RevisionConflict


def create_knowledge_publication_router(handler, authenticate) -> APIRouter:
    router = APIRouter(tags=["knowledge-publications"])

    @router.post(
        "/knowledge-publications",
        response_model=KnowledgePublicationResponse,
    )
    def publish_knowledge(
        request: KnowledgePublicationRequest,
        response: Response,
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ) -> KnowledgePublicationResponse:
        domain_input = PublishKnowledgeInput(
            tenant_id=principal.tenant_id,
            project_key=request.project_key,
            environment_name=request.environment,
            deployment_id=request.deployment_id,
            version=request.version,
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
