import os
from collections.abc import Callable

from fastapi import APIRouter, FastAPI
from sqlalchemy.orm import Session, sessionmaker

from api.adapters.http.service_account_routes import create_service_account_router
from api.adapters.http.token_routes import create_token_router
from api.adapters.http.user_routes import create_user_router
from api.application.services.service_account_service import ServiceAccountService
from api.application.services.token_service import TokenService
from api.application.services.user_service import UserService
from core.infrastructure.postgres.config import PostgresSettings
from core.infrastructure.postgres.engine_factory import PostgresEngineFactory
from core.infrastructure.postgres.repositories.api_service_account_repository import (
    ApiServiceAccountRepository,
)
from core.infrastructure.postgres.repositories.api_token_repository import ApiTokenRepository
from core.infrastructure.postgres.repositories.api_user_repository import ApiUserRepository


def create_app(session_factory: Callable[[], Session] | None = None) -> FastAPI:
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
    application = FastAPI(
        title="Harness Memory API",
        version="1.0.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    v1_router = APIRouter(prefix="/v1")
    v1_router.include_router(create_user_router(UserService(user_repository)))
    v1_router.include_router(
        create_service_account_router(ServiceAccountService(service_account_repository))
    )
    v1_router.include_router(
        create_token_router(
            TokenService(
                token_repository,
                user_repository,
                service_account_repository=service_account_repository,
            )
        )
    )
    application.include_router(v1_router)

    @application.get("/health", tags=["health"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


app = create_app()
