from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt, StrictStr, ValidationError

from core.application.environment_context.use_cases.get_history.handler import GetHistoryHandler
from core.application.environment_context.use_cases.get_history.inbound import GetHistoryInput
from core.application.snapshot_publication.errors.missing_tenant_context import (
    MissingTenantContext,
)
from harness_memory_mcp.services.authorization_failure import AuthorizationFailure
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_get_history(
    server: FastMCP, handler: GetHistoryHandler, tenant_context: TenantContextProvider
):
    @server.tool(
        name="get_history",
        description=(
            "Read snapshot history for one project environment, newest revision first. "
            "Use search_projects to find the project key, environment, and current_snapshot_id. "
            "Omit snapshot_id to list snapshots. Supply a returned snapshot_id to list its "
            "added, removed, and modified entity keys against the preceding revision. "
            "The first revision compares against an empty state. Pages are bounded. "
            "Use query to find changed entities by literal terms in keys, names, or metadata "
            "on either side of a change, including removals. Returns before/after references. "
            "Only current_snapshot_id is current; older snapshots are historical. Requires memory:read."
        ),
    )
    def get_history(
        project_key: Annotated[
            StrictStr, Field(description="Exact project key from search_projects.key.")
        ],
        environment: Annotated[
            StrictStr,
            Field(description="Exact environment name from search_projects.environments[].name."),
        ],
        snapshot_id: Annotated[
            UUID | None,
            Field(
                description="Optional snapshot_id from a get_history list page; returns entity changes for that revision."
            ),
        ] = None,
        limit: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=500,
                description="Maximum snapshots or entity keys per category, from 1 to 500.",
            ),
        ] = 100,
        offset: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=10000,
                description="Snapshots or entity keys per category to skip, from 0 to 10000.",
            ),
        ] = 0,
        tenant_id: Annotated[
            StrictStr | None,
            Field(
                description="Tenant ID from search_projects; narrows authenticated scope and disambiguates repeated keys."
            ),
        ] = None,
        query: Annotated[
            StrictStr | None,
            Field(
                max_length=255,
                description="Optional case-insensitive literal phrase in changed entity keys, names, or metadata before or after a change; filters before pagination.",
            ),
        ] = None,
    ):
        try:
            context = tenant_context.require_scope("memory:read")
            if tenant_id is not None and not context.is_admin and tenant_id != context.tenant_id:
                raise ValueError("tenant selector is outside the trusted read scope")
            request = GetHistoryInput(
                project_key=project_key,
                environment=environment,
                snapshot_id=snapshot_id,
                limit=limit,
                offset=offset,
                tenant_id=tenant_id if context.is_admin else context.tenant_id,
                query=query,
            )
            return handler.execute(request)
        except (ValidationError, ValueError, LookupError):
            return {"error": {"code": "INVALID_ARGUMENT", "message": "invalid history selectors"}}
        except AuthorizationFailure:
            return {"error": {"code": "READ_UNAUTHORIZED", "message": "memory:read is required"}}
        except MissingTenantContext:
            return {
                "error": {
                    "code": "MISSING_TENANT_CONTEXT",
                    "message": "trusted tenant context is required",
                }
            }
        except Exception:
            return {"error": {"code": "INTERNAL_ERROR", "message": "history read failed"}}

    return get_history
