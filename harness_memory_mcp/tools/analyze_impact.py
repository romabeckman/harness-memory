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
from harness_memory_mcp.services.audited_operation import ExecuteAuditedOperation
from harness_memory_mcp.services.impact_response_mapper import ImpactResponseMapper
from harness_memory_mcp.services.tenant_context import TenantContextProvider


def register_analyze_impact(
    server: FastMCP,
    handler: AnalyzeImpactHandler,
    tenant_context: TenantContextProvider,
    response_mapper: ImpactResponseMapper | None = None,
    audited_operation: ExecuteAuditedOperation | None = None,
):
    mapper = response_mapper or ImpactResponseMapper()

    @server.tool(
        name="analyze_impact",
        description=(
            "Analyze downstream consumers and affected projects for a proposed entity change. "
            "Exactly one target entity is required across supported target fields. "
            "Returns bounded paths, evidence, and unknowns; it does not guess missing impacts. "
            "Requires memory:impact."
        ),
    )
    def analyze_impact(
        entity_id: Annotated[
            UUID | None,
            Field(
                description="Legacy identifier of the changed entity; retained for compatibility."
            ),
        ] = None,
        changed_entity_id: Annotated[
            UUID | None,
            Field(description="Identifier of the entity being changed."),
        ] = None,
        target_entity_id: Annotated[
            UUID | None,
            Field(description="Alternative identifier for the entity being changed."),
        ] = None,
        change: Annotated[
            ChangeDescription | None,
            Field(
                description=(
                    "Structured change details: target entity, change type, summary, "
                    "and affected fields."
                )
            ),
        ] = None,
        change_type: Annotated[
            StrictStr,
            Field(
                min_length=1,
                max_length=64,
                description="Change category, such as contract or implementation.",
            ),
        ] = "contract",
        description: Annotated[
            StrictStr,
            Field(max_length=4096, description="Human-readable summary of the proposed change."),
        ] = "",
        changed_fields: Annotated[
            tuple[StrictStr, ...],
            Field(description="Names of the entity fields affected by the change."),
        ] = (),
        max_depth: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=8,
                description="Maximum relationship hops when tracing impact, from 1 to 8.",
            ),
        ] = 4,
        max_consumers: Annotated[
            StrictInt,
            Field(
                ge=1,
                le=500,
                description="Maximum downstream consumers to evaluate, from 1 to 500.",
            ),
        ] = 100,
        max_paths: Annotated[
            StrictInt,
            Field(ge=1, le=100, description="Maximum dependency paths to return, from 1 to 100."),
        ] = 25,
        evidence_limit: Annotated[
            StrictInt,
            Field(
                ge=0,
                le=20,
                description="Maximum evidence items per relationship, from 0 to 20.",
            ),
        ] = 5,
        owner_limit: Annotated[
            StrictInt,
            Field(ge=0, le=20, description="Maximum owner records per entity, from 0 to 20."),
        ] = 5,
        max_result_bytes: Annotated[
            StrictInt,
            Field(
                ge=64 * 1024,
                le=16 * 1024 * 1024,
                description="Maximum serialized result size in bytes, from 64 KiB to 16 MiB.",
            ),
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
            scope = TenantScope(context.tenant_id, context.is_admin)
            if audited_operation is None:
                result = handler.execute(request, scope)
            else:
                principal = tenant_context.security_context.current() or AuthenticatedPrincipal(
                    subject="in-process",
                    tenant_id=context.tenant_id,
                    scopes=frozenset({"memory:impact"}),
                )
                result = audited_operation.execute(
                    operation=lambda: handler.execute(request, scope),
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
