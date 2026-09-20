from fastapi import APIRouter, Header, Response, status

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


def create_knowledge_publication_router(handler) -> APIRouter:
    router = APIRouter(tags=["knowledge-publications"])

    @router.post(
        "/knowledge-publications",
        response_model=KnowledgePublicationResponse,
    )
    def publish_knowledge(
        request: KnowledgePublicationRequest,
        response: Response,
        x_tenant_id: str | None = Header(None, alias="X-Tenant-ID"),
    ) -> KnowledgePublicationResponse:
        tenant_id = x_tenant_id or "default"
        domain_input = PublishKnowledgeInput(
            tenant_id=tenant_id,
            project_key=request.project_key,
            environment_name=request.environment,
            deployment_id=request.deployment_id,
            version=request.version,
            entities=tuple(request.entities),
            relations=tuple(request.relations),
            evidence=tuple(request.evidence),
        )
        output = handler.execute(domain_input)

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
