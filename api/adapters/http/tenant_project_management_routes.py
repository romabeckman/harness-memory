from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from api.adapters.http.schemas.project_create import ProjectCreate
from api.adapters.http.schemas.project_environment_create import ProjectEnvironmentCreate
from api.adapters.http.schemas.project_update import ProjectUpdate
from api.adapters.http.schemas.tenant_create import TenantCreate
from api.adapters.http.schemas.tenant_update import TenantUpdate
from api.application.services.project_management_service import ProjectManagementService
from api.application.services.project_environment_management_service import (
    ProjectEnvironmentManagementService,
)
from api.application.services.tenant_management_service import TenantManagementService


def create_tenant_project_management_router(
    tenants: TenantManagementService,
    projects: ProjectManagementService,
    project_environments: ProjectEnvironmentManagementService,
) -> APIRouter:
    router = APIRouter(tags=["resource-management"])

    @router.post("/tenants", status_code=status.HTTP_201_CREATED)
    def create_tenant(request: TenantCreate):
        try:
            return tenants.create(request.key, request.name, request.metadata)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.patch("/tenants/{tenant_id}")
    def update_tenant(tenant_id: UUID, request: TenantUpdate):
        try:
            return tenants.update(tenant_id, request.model_dump(exclude_unset=True))
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_tenant(tenant_id: UUID):
        try:
            tenants.delete(tenant_id)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return None

    @router.post("/projects", status_code=status.HTTP_201_CREATED)
    def create_project(request: ProjectCreate):
        try:
            return projects.create(request.tenant_id, request.key, request.name, request.metadata)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.post(
        "/projects/{project_key}/environments", status_code=status.HTTP_201_CREATED
    )
    def create_project_environment(
        project_key: str,
        request: ProjectEnvironmentCreate,
        tenant_id: UUID = Query(...),
    ):
        try:
            return project_environments.create(tenant_id, project_key, request.name)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.patch("/projects/{project_key}")
    def update_project(
        project_key: str,
        request: ProjectUpdate,
        tenant_id: UUID = Query(...),
    ):
        try:
            return projects.update(
                tenant_id, project_key, request.model_dump(exclude_unset=True)
            )
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error

    @router.delete("/projects/{project_key}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_project(project_key: str, tenant_id: UUID = Query(...)):
        try:
            projects.delete(tenant_id, project_key)
        except LookupError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return None

    return router
