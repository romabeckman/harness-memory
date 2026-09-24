from typing import Annotated

from fastmcp import FastMCP
from pydantic import Field, StrictInt, StrictStr, ValidationError

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.entity_discovery.errors.project_search_failure import ProjectSearchFailure
from core.application.entity_discovery.use_cases.search_projects.handler import (
    SearchProjectsHandler,
)
from core.application.entity_discovery.use_cases.search_projects.inbound import (
    SearchProjectsInput,
)
from core.application.snapshot_publication.errors.missing_tenant_context import (
    MissingTenantContext,
)
from harness_memory_mcp.services.authorization_failure import AuthorizationFailure
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_search_projects(
    server: FastMCP,
    handler: SearchProjectsHandler,
    tenant_context: TenantContextProvider,
):
    @server.tool(
        name="search_projects",
        description=(
            "Find project records, including projects without published snapshots. "
            "Use key for exact project lookup or query for a partial key or name. "
            "Returns tenant and project identifiers, environment names, and snapshot status. Requires memory:read."
        ),
    )
    def search_projects(
        key: Annotated[
            StrictStr | None,
            Field(max_length=255, description="Match one project key exactly."),
        ] = None,
        query: Annotated[
            StrictStr | None,
            Field(
                max_length=255,
                description="Find a case-insensitive substring in project keys or names.",
            ),
        ] = None,
        limit: Annotated[
            StrictInt,
            Field(ge=1, le=100, description="Maximum number of results, from 1 to 100."),
        ] = 25,
        offset: Annotated[
            StrictInt,
            Field(ge=0, le=10000, description="Number of matching projects to skip."),
        ] = 0,
    ):
        try:
            request = SearchProjectsInput(
                key=key,
                query=query,
                limit=limit,
                offset=offset,
            )
            if request.key is None and request.query is None:
                raise ValueError("at least one project discovery filter is required")
            context = tenant_context.require_scope("memory:read")
            result = handler.execute(
                request,
                TenantScope(context.tenant_id, context.is_admin),
            )
            return result.model_dump(mode="json", exclude_none=True)
        except ValidationError:
            return {
                "status": "ERROR",
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": "invalid project search parameters",
                },
            }
        except ValueError:
            return {
                "status": "ERROR",
                "error": {
                    "code": "INVALID_ARGUMENT",
                    "message": "provide an exact key or a project query",
                },
            }
        except AuthorizationFailure:
            return {
                "status": "ERROR",
                "error": {
                    "code": "READ_UNAUTHORIZED",
                    "message": "project search requires trusted memory:read access",
                },
            }
        except MissingTenantContext:
            return {
                "status": "ERROR",
                "error": {
                    "code": "MISSING_TENANT_CONTEXT",
                    "message": "trusted tenant context is required",
                },
            }
        except ProjectSearchFailure:
            return {
                "status": "ERROR",
                "error": {
                    "code": "PROJECT_SEARCH_FAILED",
                    "message": "project search failed",
                },
            }
        except Exception:
            return {
                "status": "ERROR",
                "error": {
                    "code": "PROJECT_SEARCH_FAILED",
                    "message": "project search failed",
                },
            }

    return search_projects
