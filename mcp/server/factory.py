from fastmcp import FastMCP

from core.application.snapshot_publication.use_cases.publish_project_snapshot.handler import (
    PublishProjectSnapshotHandler,
)
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory
from core.infrastructure.postgres.repositories.entity_search_repository import (
    PostgresEntitySearchRepository,
)
from core.infrastructure.postgres.repositories.integration_path_repository import (
    PostgresIntegrationPathRepository,
)
from core.infrastructure.postgres.repositories.relationship_query_repository import (
    PostgresRelationshipQueryRepository,
)
from core.infrastructure.postgres.repositories.snapshot_publication_repository import (
    PostgresSnapshotPublicationRepository,
)
from mcp.config import RuntimeSettings
from mcp.services.tenant_context import TenantContextProvider
from mcp.tools.find_integration_paths import register_find_integration_paths
from mcp.tools.get_context import register_get_context
from mcp.tools.get_dependencies import register_get_dependencies
from mcp.tools.publish_project_snapshot import register_publish_project_snapshot
from mcp.tools.search_entities import register_search_entities


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
) -> FastMCP:
    if settings is not None:
        settings.model_validate(settings.model_dump())
    server = FastMCP(name="harness-memory")
    if handler is None and repository is not None:
        handler = PublishProjectSnapshotHandler(repository)
    if handler is None and settings is not None and settings.database_url is not None:
        postgres = PostgresSettings(database_url=settings.database_url)
        engine = PostgresEngineFactory.create(postgres)
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
    context = tenant_context or TenantContextProvider()
    integration_path_repository = (
        integration_path_repository
        or integration_repository
        or integration_path_query_repository
    )
    if handler is not None:
        register_publish_project_snapshot(server, handler, context)
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
    if get_dependencies_handler is not None:
        register_get_dependencies(server, get_dependencies_handler, context)
    if find_integration_paths_handler is None and integration_path_repository is not None:
        from core.application.integration_paths.use_cases.find_integration_paths.handler import (
            FindIntegrationPathsHandler,
        )

        find_integration_paths_handler = FindIntegrationPathsHandler(integration_path_repository)
    if find_integration_paths_handler is not None:
        register_find_integration_paths(server, find_integration_paths_handler, context)
    return server


class CreateMCPServer:
    def execute(self, settings: RuntimeSettings | None = None) -> FastMCP:
        return create_mcp_server(settings)
