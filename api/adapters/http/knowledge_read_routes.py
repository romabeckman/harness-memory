from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def create_knowledge_read_router(repository, authenticate, authenticate_publication_target=None) -> APIRouter:
    router = APIRouter(tags=["knowledge-reads"])

    def read_tenant(principal: AuthenticatedPrincipal, requested_tenant: UUID | None) -> str | None:
        return str(requested_tenant) if requested_tenant is not None else None

    @router.get("/tenants")
    def tenants(
        key: str | None = None,
        status: str | None = None,
        q: str | None = None,
        tenant_id: UUID | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        return repository.tenants(
            tenant_id=read_tenant(principal, tenant_id), key=key, status=status,
            query=q, limit=limit, offset=offset,
        )

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
        tenant = repository.tenant(str(tenant_id))
        if tenant is None:
            raise HTTPException(status_code=404, detail="tenant not found")
        return tenant

    @router.get("/projects")
    def projects(
        tenant_id: UUID | None = None,
        key: str | None = None,
        name: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate_publication_target or authenticate),
    ):
        return repository.projects(
            read_tenant(principal, tenant_id), key=key, name=name, query=q,
            limit=limit, offset=offset,
        )

    @router.get("/projects/{project_key}")
    def project(
        project_key: str,
        tenant_id: UUID | None = None,
        principal: AuthenticatedPrincipal = Depends(authenticate_publication_target or authenticate),
    ):
        try:
            result = repository.project(read_tenant(principal, tenant_id), project_key)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="project not found")
        return result

    @router.get("/projects/{project_key}/snapshots")
    def snapshots(
        project_key: str,
        tenant_id: UUID | None = None,
        environment_id: UUID | None = None,
        revision: int | None = None,
        payload_hash: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        try:
            result = repository.snapshots(
                read_tenant(principal, tenant_id), project_key,
                environment_id=environment_id, revision=revision, payload_hash=payload_hash,
                limit=limit, offset=offset,
            )
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        if result is None:
            raise HTTPException(status_code=404, detail="project not found")
        return result

    @router.get("/snapshots/{snapshot_id}")
    def snapshot(snapshot_id: UUID, principal: AuthenticatedPrincipal = Depends(authenticate)):
        result = repository.snapshot(None, snapshot_id)
        if result is None:
            raise HTTPException(status_code=404, detail="snapshot not found")
        return result

    return router
