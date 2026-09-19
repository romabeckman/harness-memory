from fastmcp import FastMCP

from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from mcp.services.publication_response_mapper import PublicationResponseMapper
from mcp.services.tenant_context import TenantContextProvider


def register_publish_project_snapshot(
    server: FastMCP,
    handler: PublishProjectSnapshotHandler,
    tenant_context: TenantContextProvider,
    response_mapper: PublicationResponseMapper | None = None,
):
    mapper = response_mapper or PublicationResponseMapper()

    @server.tool(name="publish_project_snapshot")
    def publish_project_snapshot(request: PublishProjectSnapshotInput):
        try:
            result = handler.execute(request, tenant_context.require())
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return publish_project_snapshot
