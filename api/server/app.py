import os
from collections.abc import Callable

from fastapi import APIRouter, Depends, FastAPI
from sqlalchemy.orm import Session, sessionmaker

from api.adapters.http.api_security import ApiSecurity
from api.adapters.http.knowledge_publication_routes import (
    create_knowledge_publication_router,
)
from api.adapters.http.knowledge_read_routes import create_knowledge_read_router
from api.adapters.http.knowledge_search_routes import create_knowledge_search_router
from api.adapters.http.service_account_routes import create_service_account_router
from api.adapters.http.tenant_project_management_routes import (
    create_tenant_project_management_router,
)
from api.adapters.http.token_routes import create_token_router
from api.adapters.http.user_routes import create_user_router
from api.application.services.service_account_service import ServiceAccountService
from api.application.services.token_service import TokenService
from api.application.services.project_management_service import ProjectManagementService
from api.application.services.tenant_management_service import TenantManagementService
from api.application.services.user_service import UserService
from core.application.knowledge_publication.use_cases.get_publication_baseline import (
    GetPublicationBaseline,
)
from core.application.knowledge_publication.use_cases.publish_knowledge.handler import (
    PublishKnowledgeHandler,
)
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory
from core.infrastructure.postgres.repositories.api_service_account_repository import (
    ApiServiceAccountRepository,
)
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository
from core.infrastructure.postgres.repositories.environment_repository import (
    PostgresEnvironmentRepository,
)
from core.infrastructure.postgres.repositories.knowledge_publication_repository import (
    PostgresKnowledgePublicationRepository,
)
from core.infrastructure.postgres.repositories.knowledge_read_repository import (
    KnowledgeReadRepository,
)
from core.infrastructure.postgres.repositories.tenant_project_management_repository import (
    PostgresTenantProjectManagementRepository,
)


def create_app(
    session_factory: Callable[[], Session] | None = None,
    *,
    admin_token: str | None = None,
    read_api_key: str | None = None,
) -> FastAPI:
    if session_factory is None:
        settings = PostgresSettings(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg2://harness_memory:harness_memory@localhost:5432/harness_memory",
            )
        )
        session_factory = sessionmaker(
            bind=PostgresEngineFactory.create(settings), expire_on_commit=False
        )
    user_repository = ApiUserRepository(session_factory)
    service_account_repository = ApiServiceAccountRepository(session_factory)
    token_repository = ApiTokenRepository(session_factory)
    read_repository = KnowledgeReadRepository(session_factory)
    security = ApiSecurity(
        token_repository,
        admin_token or os.getenv("API_ADMIN_TOKEN"),
        read_api_key or os.getenv("HARNESS_MEMORY_API_KEY"),
    )
    application = FastAPI(
        title="Harness Memory API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    v1_router = APIRouter(prefix="/v1")
    management_router = APIRouter(dependencies=[Depends(security.require_admin)])
    management_router.include_router(create_user_router(UserService(user_repository)))
    management_router.include_router(
        create_service_account_router(ServiceAccountService(service_account_repository))
    )
    management_router.include_router(
        create_token_router(
            TokenService(
                token_repository,
                user_repository,
                service_account_repository=service_account_repository,
            )
        )
    )
    resource_repository = PostgresTenantProjectManagementRepository(session_factory)
    management_router.include_router(
        create_tenant_project_management_router(
            TenantManagementService(resource_repository),
            ProjectManagementService(resource_repository),
        )
    )
    v1_router.include_router(management_router)
    v1_router.include_router(create_knowledge_read_router(read_repository, security.require_reader))
    v1_router.include_router(create_knowledge_search_router(read_repository, security.require_reader))
    env_repository = PostgresEnvironmentRepository(session_factory=session_factory)
    pub_repository = PostgresKnowledgePublicationRepository(session_factory=session_factory)
    publish_handler = PublishKnowledgeHandler(
        publication_repository=pub_repository,
        environment_repository=env_repository,
    )
    v1_router.include_router(
        create_knowledge_publication_router(publish_handler, security.require_publisher,
            GetPublicationBaseline(pub_repository), security.require_baseline_reader,
            tenant_exists=lambda tenant_id: read_repository.tenant(tenant_id) is not None)
    )
    application.include_router(v1_router)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
