from uuid import UUID

from fastapi import APIRouter, Depends, Query

from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal


def create_knowledge_search_router(repository, authenticate, authenticate_publication_target=None) -> APIRouter:
    router = APIRouter(tags=["knowledge-search"])

    def tenant_scope(
        principal: AuthenticatedPrincipal, requested_tenant: UUID | None
    ) -> str | None:
        return str(requested_tenant) if requested_tenant is not None else None

    @router.get("/environments")
    def environments(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        name: str | None = None,
        environment_type: str | None = Query(default=None, alias="type"),
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate_publication_target or authenticate),
    ):
        return repository.environments(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            name=name,
            environment_type=environment_type,
            query=q,
            limit=limit,
            offset=offset,
        )

    @router.get("/knowledge-publications")
    def publications(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        environment_id: UUID | None = None,
        environment: str | None = None,
        status: str | None = None,
        version: str | None = None,
        deployment_id: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate_publication_target or authenticate),
    ):
        return repository.publications(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            environment_id=environment_id,
            environment=environment,
            status=status,
            version=version,
            deployment_id=deployment_id,
            query=q,
            limit=limit,
            offset=offset,
        )

    @router.get("/snapshots")
    def snapshots(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        environment_id: UUID | None = None,
        revision: int | None = Query(default=None, ge=0),
        schema_version: str | None = None,
        payload_hash: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        return repository.snapshot_search(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            environment_id=environment_id,
            revision=revision,
            schema_version=schema_version,
            payload_hash=payload_hash,
            limit=limit,
            offset=offset,
        )

    @router.get("/entities")
    def entities(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        project_id: UUID | None = None,
        environment: str | None = None,
        snapshot_id: UUID | None = None,
        include_history: bool = False,
        entity_type: str | None = None,
        entity_key: str | None = None,
        name: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        return repository.entities(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            project_id=project_id,
            environment=environment,
            snapshot_id=snapshot_id,
            include_history=include_history,
            entity_type=entity_type,
            entity_key=entity_key,
            name=name,
            query=q,
            limit=limit,
            offset=offset,
        )

    @router.get("/relations")
    def relations(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        snapshot_id: UUID | None = None,
        relation_type: str | None = None,
        provenance_kind: str | None = None,
        source_entity_id: UUID | None = None,
        target_entity_id: UUID | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        return repository.relations(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            snapshot_id=snapshot_id,
            relation_type=relation_type,
            provenance_kind=provenance_kind,
            source_entity_id=source_entity_id,
            target_entity_id=target_entity_id,
            query=q,
            limit=limit,
            offset=offset,
        )

    @router.get("/evidence")
    def evidence(
        tenant_id: UUID | None = None,
        project_key: str | None = None,
        snapshot_id: UUID | None = None,
        relation_id: UUID | None = None,
        source: str | None = None,
        q: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        principal: AuthenticatedPrincipal = Depends(authenticate),
    ):
        return repository.evidence(
            tenant_id=tenant_scope(principal, tenant_id),
            project_key=project_key,
            snapshot_id=snapshot_id,
            relation_id=relation_id,
            source=source,
            query=q,
            limit=limit,
            offset=offset,
        )

    return router
