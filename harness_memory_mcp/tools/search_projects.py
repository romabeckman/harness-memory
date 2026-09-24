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
            "Omit key and query to list accessible projects; supply both to combine filters. "
            "Use key for an exact, case-sensitive key or query for a case-insensitive "
            "substring of a key or name. Returns tenant and project IDs, environment "
            "names, and active snapshot status. Use these values in later entity or "
            "environment calls. Requires memory:read."
        ),
    )
    def search_projects(
        key: Annotated[
            StrictStr | None,
            Field(
                max_length=255,
                description=(
                    "Optional exact, case-sensitive project key. Omit key and query "
                    "to list projects. Blank text is invalid."
                ),
            ),
        ] = None,
        query: Annotated[
            StrictStr | None,
            Field(
                max_length=255,
                description=(
                    "Optional case-insensitive substring of project key or name. "
                    "Omit key and query to list projects. Blank text is invalid."
                ),
            ),
        ] = None,
        limit: Annotated[
            StrictInt,
            Field(ge=1, le=100, description="Maximum number of results, from 1 to 100."),
        ] = 25,
        offset: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=10000,
                description=(
                    "Matching projects to skip, from 0 to 10000; use with limit "
                    "for the next page."
                ),
            ),
        ] = 0,
    ):
        try:
            request = SearchProjectsInput(
                key=key,
                query=query,
                limit=limit,
                offset=offset,
            )
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
                    "message": "project search filters must not be blank",
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
