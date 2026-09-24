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
            "Read one entity's project, owners, relationships, dependencies, and evidence. "
            "Get entity_id and snapshot_id from search_entities; pass snapshot_id to pin "
            "the same occurrence, especially after a newer publication. Without it, "
            "only current project snapshots are searched. Add project_id or tenant_id "
            "when an identity occurs more than once. Requires memory:read."
        ),
    )
    def get_context(
        entity_id: Annotated[
            UUID,
            Field(
                description="Entity UUID from search_entities.entity_id; required for context."
            ),
        ],
        limit: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=100,
                description="Maximum related items to return, from 1 to 100.",
            ),
        ] = 25,
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
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            request = GetContextInput(
                entity_id=entity_id, limit=limit, evidence_limit=evidence_limit,
                snapshot_id=snapshot_id, project_id=project_id, tenant_id=tenant_id,
            )
            result = handler.execute(request, TenantScope(context.tenant_id, context.is_admin))
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return get_context
