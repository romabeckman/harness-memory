from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.relationship_context.use_cases.get_context.handler import GetContextHandler
from core.application.relationship_context.use_cases.get_context.inbound import GetContextInput
from harness_memory_mcp.services.relationship_response_mapper import RelationshipResponseMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_get_context(
    server: FastMCP,
    handler: GetContextHandler,
    tenant_context: TenantContextProvider,
    response_mapper: RelationshipResponseMapper | None = None,
):
    mapper = response_mapper or RelationshipResponseMapper()

    @server.tool(
        name="get_context",
        description=(
            "Read project, owner, relationship, dependency, and evidence context. "
            "Resolve the project/tenant and environment before answering project questions; "
            "pin snapshot_id to that environment's current_snapshot_id for current facts. "
            "Provide at least one of entity_id, snapshot_id, project_id, or tenant_id. "
            "With entity_id, return one matching entity context. Without entity_id, "
            "return a bounded page of current environment snapshots ordered newest to "
            "oldest. Without snapshot_id, entity_id resolves the newest current "
            "occurrence. Snapshot_id pins an immutable snapshot, including historical "
            "snapshots. Get entity_id and snapshot_id from the same search_entities result "
            "to pin context. Requires memory:read."
        ),
    )
    def get_context(
        entity_id: Annotated[
            UUID | None,
            Field(
                description=(
                    "Optional entity UUID from search_entities.entity_id. Provide at least "
                    "one of entity_id, snapshot_id, project_id, or tenant_id."
                )
            ),
        ] = None,
        limit: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=500,
                description="Maximum entity contexts per page, from 1 to 500.",
            ),
        ] = 100,
        evidence_limit: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=20,
                description="Maximum evidence items per relationship, from 0 to 20.",
            ),
        ] = 5,
        snapshot_id: Annotated[
            UUID | None,
            Field(
                description=(
                    "Snapshot UUID from search_entities.snapshot_id; pin that "
                    "occurrence instead of the current snapshot."
                )
            ),
        ] = None,
        project_id: Annotated[
            UUID | None,
            Field(
                description=(
                    "Project UUID from search_entities.project_id; disambiguate "
                    "an identity shared by projects."
                )
            ),
        ] = None,
        tenant_id: Annotated[
            str | None,
            Field(
                max_length=255,
                description=(
                    "Tenant ID from search_entities. Narrows authenticated read "
                    "scope; does not grant access."
                ),
            ),
        ] = None,
        result_limit: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=25,
                description="Maximum relations and dependencies within each context, from 1 to 25.",
            ),
        ] = 25,
        offset: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=10000,
                description="Matching entity contexts to skip, from 0 to 10000.",
            ),
        ] = 0,
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            request = GetContextInput(
                entity_id=entity_id,
                limit=limit,
                evidence_limit=evidence_limit,
                snapshot_id=snapshot_id,
                project_id=project_id,
                tenant_id=tenant_id,
                result_limit=result_limit,
                offset=offset,
            )
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return get_context
