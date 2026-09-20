from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import JWTVerifier
from fastmcp.server.middleware import AuthMiddleware

from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.application.tenant_security.use_cases.record_security_audit.handler import (
    RecordSecurityAuditHandler,
)
from core.infrastructure.postgres.alembic_runtime import AlembicRuntime
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)
from core.infrastructure.postgres.repositories.impact_analysis_repository import (
    PostgresImpactAnalysisRepository,
)
from core.infrastructure.postgres.repositories.integration_path_repository import (
    PostgresIntegrationPathRepository,
)
from core.infrastructure.postgres.repositories.memory_resource_repository import (
    PostgresMemoryResourceRepository,
)
from core.infrastructure.postgres.repositories.relationship_query_repository import (
    PostgresRelationshipQueryRepository,
)
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)
from core.infrastructure.postgres.schema_compatibility_checker import SchemaCompatibilityChecker
from core.infrastructure.postgres.verify_startup_schema import VerifyStartupSchema
from core.infrastructure.telemetry.telemetry_tracer import TelemetryTracer
from harness_memory_mcp.config import RuntimeSettings
from harness_memory_mcp.prompts import register_mcp_guidance_prompts
from harness_memory_mcp.resources.entity_resource import register_entity_resource
from harness_memory_mcp.resources.project_resource import register_project_resource
from harness_memory_mcp.resources.snapshot_resource import register_snapshot_resource
from harness_memory_mcp.server.http_security import install_http_security_error_mapping
from harness_memory_mcp.server.server_lifespan_manager import ServerLifespanManager
from harness_memory_mcp.services.audited_operation import ExecuteAuditedOperation
from harness_memory_mcp.services.authenticated_principal_factory import (
    AuthenticatedPrincipalFactory,
)
from harness_memory_mcp.services.component_scope_policy import (
    ComponentScopePolicy,
    component_scope_auth,
)
from harness_memory_mcp.services.database_token_verifier import DatabaseTokenVerifier
from harness_memory_mcp.services.security_audit_middleware import (
    AuditingTokenVerifier,
    SecurityAuditMiddleware,
)
from harness_memory_mcp.services.telemetry_middleware import TelemetryMiddleware
from harness_memory_mcp.services.tenant_context import TenantContextProvider
from harness_memory_mcp.tools.analyze_impact import register_analyze_impact
from harness_memory_mcp.tools.find_integration_paths import register_find_integration_paths
from harness_memory_mcp.tools.get_context import register_get_context
from harness_memory_mcp.tools.get_dependencies import register_get_dependencies
from harness_memory_mcp.tools.publish_project_snapshot import register_publish_project_snapshot
from harness_memory_mcp.tools.search_entities import register_search_entities


def create_mcp_server(
    settings: RuntimeSettings | None = None,
    handler: PublishProjectSnapshotHandler | None = None,
    tenant_context: TenantContextProvider | None = None,
    repository=None,
    search_handler=None,
    search_repository=None,
    entity_search_handler=None,
    entity_search_repository=None,
    relationship_repository=None,
    relationship_query_repository=None,
    get_context_handler=None,
    get_dependencies_handler=None,
    integration_path_repository=None,
    integration_repository=None,
    integration_path_query_repository=None,
    find_integration_paths_handler=None,
    impact_repository=None,
    impact_analysis_repository=None,
    impact_query_repository=None,
    impact_handler=None,
    analyze_impact_handler=None,
    memory_resource_repository=None,
    resource_repository=None,
    project_resource_handler=None,
    get_project_resource_handler=None,
    project_handler=None,
    snapshot_resource_handler=None,
    get_snapshot_resource_handler=None,
    snapshot_handler=None,
    token_verifier=None,
    auth_provider=None,
    principal_factory=None,
    audit_repository=None,
    security_audit_repository=None,
    audit_handler=None,
    security_audit_handler=None,
    production: bool = False,
    scope_policy=None,
    verify_schema: bool | None = None,
    schema_checker: SchemaCompatibilityChecker | None = None,
    alembic_runtime: AlembicRuntime | None = None,
    telemetry_tracer: TelemetryTracer | None = None,
    api_token_repository=None,
) -> FastMCP:
    if settings is not None:
        settings.model_validate(settings.model_dump())
    production = production or bool(
        settings and (settings.mcp_production or settings.mcp_require_auth)
    )
    if production and settings is None:
        raise ValueError("production HTTP settings are required")
    if production:
        settings.require_production_security()
    engine = None
    auth_provider = auth_provider or token_verifier
    if production and auth_provider is None:
        if settings.mcp_auth_mode == "database":
            if api_token_repository is None:
                postgres = PostgresSettings(database_url=settings.database_url)
                engine = PostgresEngineFactory.create(postgres)
                api_token_repository = ApiTokenRepository(engine=engine)
            auth_provider = DatabaseTokenVerifier(api_token_repository)
        else:
            auth_provider = JWTVerifier(
                jwks_uri=str(settings.mcp_jwks_uri),
                issuer=str(settings.mcp_issuer),
                audience=settings.mcp_audience,
                algorithm="RS256",
            )
            auth_provider.logger.disabled = True
    principal_factory = principal_factory or AuthenticatedPrincipalFactory(
        settings.mcp_tenant_claim if settings is not None else "tenant_id"
    )
    effective_runtime = alembic_runtime
    if (
        effective_runtime is None
        and settings is not None
        and settings.database_url is not None
        and (production or verify_schema is True)
    ):
        postgres_cfg = PostgresSettings(database_url=settings.database_url)
        effective_runtime = AlembicRuntime(postgres_cfg)
    if verify_schema is True or (
        verify_schema is None and production and effective_runtime is not None
    ):
        if effective_runtime is not None:
            VerifyStartupSchema(schema_checker).execute(effective_runtime)

    lifespan_manager = None
    if production and effective_runtime is not None:
        lifespan_manager = ServerLifespanManager(
            alembic_runtime=effective_runtime,
            telemetry_tracer=telemetry_tracer,
        )

    server = FastMCP(
        name="harness-memory",
        auth=auth_provider,
        lifespan=lifespan_manager.lifespan if lifespan_manager is not None else None,
    )
    memory_resource_repository = memory_resource_repository or resource_repository
    if handler is None and repository is not None:
        handler = PublishProjectSnapshotHandler(repository)
    if handler is None and settings is not None and settings.database_url is not None:
        postgres = PostgresSettings(database_url=settings.database_url)
        if engine is None:
            engine = PostgresEngineFactory.create(postgres)
        if lifespan_manager is not None:
            lifespan_manager.attach_engine(engine)
        repository = PostgresSnapshotPublicationRepository(engine=engine)
        handler = PublishProjectSnapshotHandler(repository)
        if (
            search_repository is None
            and search_handler is None
            and entity_search_repository is None
        ):
            search_repository = PostgresEntitySearchRepository(engine=engine)
        if relationship_repository is None and relationship_query_repository is None:
            relationship_repository = PostgresRelationshipQueryRepository(engine=engine)
        if (
            integration_path_repository is None
            and integration_repository is None
            and integration_path_query_repository is None
        ):
            integration_path_repository = PostgresIntegrationPathRepository(engine=engine)
        if (
            impact_repository is None
            and impact_analysis_repository is None
            and impact_query_repository is None
        ):
            impact_repository = PostgresImpactAnalysisRepository(engine=engine)
        if memory_resource_repository is None:
            memory_resource_repository = PostgresMemoryResourceRepository(engine=engine)
    context = tenant_context or TenantContextProvider()
    server.middleware.append(TelemetryMiddleware(tracer=telemetry_tracer, tenant_context=context))
    if production and context.has_fixed_context():
        raise ValueError("production tenant context cannot use a fixed tenant")
    audit_repository = audit_repository or security_audit_repository
    audit_handler = audit_handler or security_audit_handler
    if audit_handler is None and audit_repository is not None:
        audit_handler = RecordSecurityAuditHandler(audit_repository)
    if production and audit_handler is None:
        if settings.database_url is None:
            raise ValueError("production security audit repository is required")
        if engine is None:
            postgres = PostgresSettings(database_url=settings.database_url)
            engine = PostgresEngineFactory.create(postgres)
        from core.infrastructure.postgres.repositories.security_audit_repository import (
            PostgresSecurityAuditRepository,
        )

        audit_repository = PostgresSecurityAuditRepository(engine=engine)
        audit_handler = RecordSecurityAuditHandler(audit_repository)
    if production:
        scope_policy = scope_policy or ComponentScopePolicy()
        if auth_provider is not None:
            server.auth = AuditingTokenVerifier(auth_provider, audit_handler, principal_factory)
        server.middleware.append(
            AuthMiddleware(
                auth=component_scope_auth(
                    scope_policy,
                    audit_handler=audit_handler,
                    principal_factory=principal_factory,
                )
            )
        )
        server.middleware.append(
            SecurityAuditMiddleware(
                context,
                principal_factory,
                policy=scope_policy,
                audit_handler=audit_handler,
            )
        )
    audited_operation = (
        ExecuteAuditedOperation(audit_handler) if audit_handler is not None else None
    )
    integration_path_repository = (
        integration_path_repository or integration_repository or integration_path_query_repository
    )
    if handler is not None:
        register_publish_project_snapshot(
            server, handler, context, audited_operation=audited_operation
        )
    search_handler = search_handler or entity_search_handler
    search_repository = search_repository or entity_search_repository
    if search_handler is None and search_repository is not None:
        from core.application.entity_discovery.use_cases.search_entities.handler import (
            SearchEntitiesHandler,
        )

        search_handler = SearchEntitiesHandler(search_repository)
    if search_handler is not None:
        register_search_entities(server, search_handler, context)
    relationship_repository = relationship_repository or relationship_query_repository
    if relationship_repository is not None:
        from core.application.relationship_context.use_cases.get_context.handler import (
            GetContextHandler,
        )
        from core.application.relationship_context.use_cases.get_dependencies.handler import (
            GetDependenciesHandler,
        )

        get_context_handler = get_context_handler or GetContextHandler(relationship_repository)
        get_dependencies_handler = get_dependencies_handler or GetDependenciesHandler(
            relationship_repository
        )
    if get_context_handler is not None:
        register_get_context(server, get_context_handler, context)
        register_entity_resource(server, get_context_handler, context)
    if get_dependencies_handler is not None:
        register_get_dependencies(server, get_dependencies_handler, context)
    if find_integration_paths_handler is None and integration_path_repository is not None:
        from core.application.integration_paths.use_cases.find_integration_paths.handler import (
            FindIntegrationPathsHandler,
        )

        find_integration_paths_handler = FindIntegrationPathsHandler(integration_path_repository)
    if find_integration_paths_handler is not None:
        register_find_integration_paths(server, find_integration_paths_handler, context)
    impact_repository = impact_repository or impact_analysis_repository or impact_query_repository
    impact_handler = impact_handler or analyze_impact_handler
    if impact_handler is None and impact_repository is not None:
        from core.application.impact_analysis.use_cases.analyze_impact.handler import (
            AnalyzeImpactHandler,
        )

        impact_handler = AnalyzeImpactHandler(impact_repository)
    if impact_handler is not None:
        register_analyze_impact(
            server, impact_handler, context, audited_operation=audited_operation
        )
    project_resource_handler = (
        project_resource_handler or get_project_resource_handler or project_handler
    )
    snapshot_resource_handler = (
        snapshot_resource_handler or get_snapshot_resource_handler or snapshot_handler
    )
    if project_resource_handler is None and memory_resource_repository is not None:
        from core.application.mcp_access_surface.use_cases.get_project_resource.handler import (
            GetProjectResourceHandler,
        )

        project_resource_handler = GetProjectResourceHandler(memory_resource_repository)
    if snapshot_resource_handler is None and memory_resource_repository is not None:
        from core.application.mcp_access_surface.use_cases.get_snapshot_resource.handler import (
            GetSnapshotResourceHandler,
        )

        snapshot_resource_handler = GetSnapshotResourceHandler(memory_resource_repository)
    if project_resource_handler is not None:
        register_project_resource(server, project_resource_handler, context)
    if snapshot_resource_handler is not None:
        register_snapshot_resource(server, snapshot_resource_handler, context)
    register_mcp_guidance_prompts(server)
    if production:
        install_http_security_error_mapping(server)
    return server


class CreateMCPServer:
    def execute(self, settings: RuntimeSettings | None = None) -> FastMCP:
        return create_mcp_server(settings)
