from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.adapters.http.schemas.linked_project_summary_schema import (
    LinkedProjectSummarySchema,
)
from api.adapters.http.schemas.project_link_create import ProjectLinkCreateRequest
from api.adapters.http.schemas.project_link_response import ProjectLinkResponse
from api.application.services.project_link_management_service import (
    ProjectLinkManagementService,
)
from api.application.services.project_management_service import ProjectManagementService


def create_project_link_router(
    project_links: ProjectLinkManagementService,
    projects: ProjectManagementService | None = None,
) -> APIRouter:
    router = APIRouter(tags=["project-links"])

    @router.post(
        "/projects/{project_key}/links",
        response_model=ProjectLinkResponse,
        status_code=status.HTTP_201_CREATED,
    )
    def create_project_link(
        project_key: str,
        request: ProjectLinkCreateRequest,
        tenant_id: UUID = Query(...),
    ) -> ProjectLinkResponse:
        try:
            created_link = project_links.create_link(
                origin_tenant_id=tenant_id,
                origin_key=project_key,
                target_key=request.target_project_key,
                target_tenant_id=request.target_tenant_id,
            )
            target_tenant = (
                request.target_tenant_id if request.target_tenant_id is not None else tenant_id
            )
            linked_proj = None
            if projects is not None:
                try:
                    linked_proj = projects.get(target_tenant, request.target_project_key)
                except LookupError:
                    pass

            target_id = (
                UUID(linked_proj["id"])
                if linked_proj
                else (
                    created_link.pair.project_b_id
                    if created_link.pair.project_a_id != created_link.pair.project_b_id
                    else created_link.pair.project_a_id
                )
            )
            target_name = linked_proj.get("name") if linked_proj else None

            return ProjectLinkResponse(
                id=created_link.id,
                linked_project=LinkedProjectSummarySchema(
                    project_id=target_id,
                    key=request.target_project_key,
                    name=target_name,
                    tenant_id=target_tenant,
                ),
                created_at=created_link.created_at,
            )
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except ValueError as error:
            msg = str(error)
            if "cannot link project to itself" in msg:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg
                ) from error
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from error

    @router.get(
        "/projects/{project_key}/links",
        response_model=list[LinkedProjectSummarySchema],
        status_code=status.HTTP_200_OK,
    )
    def list_project_links(
        project_key: str,
        tenant_id: UUID = Query(...),
    ) -> list[LinkedProjectSummarySchema]:
        try:
            summaries = project_links.list_links(tenant_id, project_key)
            return [
                LinkedProjectSummarySchema(
                    project_id=s.project_id,
                    key=s.key,
                    name=s.name,
                    tenant_id=s.tenant_id,
                )
                for s in summaries
            ]
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    @router.delete(
        "/projects/{project_key}/links/{target_project_key}",
        status_code=status.HTTP_204_NO_CONTENT,
    )
    def delete_project_link(
        project_key: str,
        target_project_key: str,
        tenant_id: UUID = Query(...),
        target_tenant_id: UUID | None = Query(None),
    ) -> None:
        try:
            project_links.delete_link(
                tenant_id,
                project_key,
                target_project_key,
                target_tenant_id,
            )
        except LookupError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
        return None

    return router
