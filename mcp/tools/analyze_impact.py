from typing import Annotated
from uuid import UUID

from fastmcp import FastMCP
from pydantic import Field, StrictInt, StrictStr

from core.application.entity_discovery.contracts.tenant_scope import TenantScope
from core.application.impact_analysis.contracts.change_description import ChangeDescription
from core.application.impact_analysis.types.impact_analysis_bounds import ImpactAnalysisBounds
from core.application.impact_analysis.use_cases.analyze_impact.handler import AnalyzeImpactHandler
from core.application.impact_analysis.use_cases.analyze_impact.inbound import AnalyzeImpactInput
from core.domain.tenant_security.types.audit_event_type import AuditEventType
from core.domain.tenant_security.value_objects.authenticated_principal import AuthenticatedPrincipal
from mcp.services.audited_operation import ExecuteAuditedOperation
from mcp.services.impact_response_mapper import ImpactResponseMapper
from mcp.services.tenant_context import TenantContextProvider


def register_analyze_impact(
    server: FastMCP,
    handler: AnalyzeImpactHandler,
    tenant_context: TenantContextProvider,
    response_mapper: ImpactResponseMapper | None = None,
    audited_operation: ExecuteAuditedOperation | None = None,
):
    mapper = response_mapper or ImpactResponseMapper()

    @server.tool(name="analyze_impact")
    def analyze_impact(
        entity_id: UUID | None = None,
        changed_entity_id: UUID | None = None,
        target_entity_id: UUID | None = None,
        change: ChangeDescription | None = None,
        change_type: Annotated[StrictStr, Field(min_length=1, max_length=64)] = "contract",
        description: Annotated[StrictStr, Field(max_length=4096)] = "",
        changed_fields: tuple[StrictStr, ...] = (),
        max_depth: Annotated[StrictInt, Field(ge=1, le=8)] = 4,
        max_consumers: Annotated[StrictInt, Field(ge=1, le=500)] = 100,
        max_paths: Annotated[StrictInt, Field(ge=1, le=100)] = 25,
        evidence_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
        owner_limit: Annotated[StrictInt, Field(ge=0, le=20)] = 5,
        max_result_bytes: Annotated[
            StrictInt, Field(ge=64 * 1024, le=16 * 1024 * 1024)
        ] = 1024 * 1024,
    ):
        try:
            context = tenant_context.require_scope("memory:impact")
            request = AnalyzeImpactInput(
                entity_id=entity_id,
                changed_entity_id=changed_entity_id,
                target_entity_id=target_entity_id,
                change=change,
                change_type=change_type,
                description=description,
                changed_fields=changed_fields,
                bounds=ImpactAnalysisBounds(
                    max_depth=max_depth,
                    max_consumers=max_consumers,
                    max_paths=max_paths,
                    evidence_limit=evidence_limit,
                    owner_limit=owner_limit,
                    max_result_bytes=max_result_bytes,
                ),
            )
            if audited_operation is None:
                result = handler.execute(request, TenantScope(context.tenant_id))
            else:
                principal = tenant_context.security_context.current() or AuthenticatedPrincipal(
                    subject="in-process",
                    tenant_id=context.tenant_id,
                    scopes=frozenset({"memory:impact"}),
                )
                result = audited_operation.execute(
                    operation=lambda: handler.execute(request, TenantScope(context.tenant_id)),
                    principal=principal,
                    request_id=None,
                    event_type=AuditEventType.IMPACT_ANALYSIS,
                    component="analyze_impact",
                    required_scope="memory:impact",
                    safe_details={
                        "entity_id": str(request.changed_entity_id or request.entity_id),
                        "change_type": change_type,
                    },
                )
            return mapper.success(result)
        except Exception as error:
            return mapper.failure(error)

    return analyze_impact
