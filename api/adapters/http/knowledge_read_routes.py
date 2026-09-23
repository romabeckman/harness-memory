from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def create_knowledge_read_router(repository, authenticate) -> APIRouter:
    router = APIRouter(tags=["knowledge-reads"])

    def read_tenant(principal: AuthenticatedPrincipal, requested_tenant: UUID | None) -> str | None:
        if principal.is_admin:
            return str(requested_tenant) if requested_tenant is not None else None
        return principal.tenant_id

    @router.get("/tenants")
    def tenants(principal: AuthenticatedPrincipal = Depends(authenticate)):
        if principal.is_admin:
            return repository.tenants()
        tenant = repository.tenant(principal.tenant_id)
        return [tenant] if tenant is not None else []

    @router.get("/tenants/current")
    def current_tenant(principal: AuthenticatedPrincipal = Depends(authenticate)):
        if principal.is_admin:
            raise HTTPException(status_code=400, detail="administrator has no current tenant")
        tenant = repository.tenant(principal.tenant_id)
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant not found")
        return tenant

    @router.get("/tenants/{tenant_id}")
    def tenant_by_id(
        tenant_id: UUID,
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        if not principal.is_admin and str(tenant_id) != principal.tenant_id:
            raise HTTPException(status_code=404, detail="tenant not found")
        tenant = repository.tenant(str(tenant_id))
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant not found")
        return tenant

    @router.get("/projects")
    def projects(principal: AuthenticatedPrincipal = Depends(authenticate)):
        return repository.projects(read_tenant(principal, None))

    @router.get("/projects/{project_key}")
    def project(project_key: str, tenant_id: UUID | None = None,
                principal: AuthenticatedPrincipal = Depends(authenticate)):
        try:
            result = repository.project(read_tenant(principal, tenant_id), project_key)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="project not found")
        return result

    @router.get("/projects/{project_key}/snapshots")
    def snapshots(project_key: str, tenant_id: UUID | None = None,
                  principal: AuthenticatedPrincipal = Depends(authenticate)):
        try:
            result = repository.snapshots(read_tenant(principal, tenant_id), project_key)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="project not found")
        return result

    @router.get("/snapshots/{snapshot_id}")
    def snapshot(snapshot_id: UUID, principal: AuthenticatedPrincipal = Depends(authenticate)):
        tenant_id = None if principal.is_admin else principal.tenant_id
        result = repository.snapshot(tenant_id, snapshot_id)
        if result is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return result

    return router
