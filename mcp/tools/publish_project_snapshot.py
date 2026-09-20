from fastmcp import FastMCP

from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.snapshot_publication.use_cases.publish_project_snapshot.inbound import (
    PublishProjectSnapshotInput,
)
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal
from mcp.services.audited_operation import ExecuteAuditedOperation
from mcp.services.publication_response_mapper import PublicationResponseMapper
from mcp.services.tenant_context import TenantContextProvider


def register_publish_project_snapshot(
    server: FastMCP,
    handler: PublishProjectSnapshotHandler,
    tenant_context: TenantContextProvider,
    response_mapper: PublicationResponseMapper | None = None,
    audited_operation: ExecuteAuditedOperation | None = None,
):
    mapper = response_mapper or PublicationResponseMapper()

    @server.tool(name="publish_project_snapshot")
    def publish_project_snapshot(request: PublishProjectSnapshotInput):
        try:
            context = tenant_context.require_scope("memory:publish")
            if audited_operation is None:
                result = handler.execute(request, context)
            else:
                principal = tenant_context.security_context.current() or AuthenticatedPrincipal(
                    subject="in-process",
                    tenant_id=context.tenant_id,
                    scopes=frozenset({"memory:publish"}),
                )
                result = audited_operation.execute(
                    operation=lambda: handler.execute(request, context),
                    principal=principal,
                    request_id=None,
                    event_type=AuditEventType.PUBLICATION,
                    component="publish_project_snapshot",
                    required_scope="memory:publish",
                    safe_details={
                        "project_key": request.project.key,
                        "revision": str(request.revision),
                    },
                )
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return publish_project_snapshot
