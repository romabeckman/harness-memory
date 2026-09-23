from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.application.ports.tenant_project_management_repository import (
    TenantProjectManagementRepository,
)
from core.infrastructure.postgres.models.api_service_account import ApiServiceAccount
from core.infrastructure.postgres.models.api_user import ApiUser
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.knowledge_publication import KnowledgePublication
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant


class PostgresTenantProjectManagementRepository(TenantProjectManagementRepository):
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def create_tenant(self, key: str, name: str, metadata: dict[str, Any]) -> dict:
        try:
            with self._session_factory() as session, session.begin():
                tenant = Tenant(
                    id=uuid4(), key=key, name=name, status="active", metadata_json=metadata
                )
                session.add(tenant)
                session.flush()
                return self._tenant(tenant)
        except IntegrityError as error:
            raise ValueError("tenant key already exists") from error

    def get_tenant(self, tenant_id: UUID) -> dict | None:
        with self._session_factory() as session:
            tenant = session.get(Tenant, tenant_id)
            return self._tenant(tenant) if tenant else None

    def update_tenant(self, tenant_id: UUID, values: dict[str, Any]) -> dict | None:
        try:
            with self._session_factory() as session, session.begin():
                tenant = session.get(Tenant, tenant_id)
                if tenant is None:
                    return None
                if values.get("name") is not None:
                    tenant.name = values["name"]
                if values.get("status") is not None:
                    tenant.status = values["status"]
                if values.get("metadata") is not None:
                    tenant.metadata_json = values["metadata"]
                tenant.updated_at = datetime.now(UTC)
                session.flush()
                return self._tenant(tenant)
        except IntegrityError as error:
            raise ValueError("tenant update violates a data constraint") from error

    def delete_tenant(self, tenant_id: UUID) -> bool:
        with self._session_factory() as session, session.begin():
            tenant = session.get(Tenant, tenant_id)
            if tenant is None:
                return False
            if any(
                session.scalar(select(model.id).where(model.tenant_id == tenant_id).limit(1))
                is not None
                for model in (Project, ApiUser, ApiServiceAccount)
            ):
                raise ValueError("tenant cannot be deleted while it has projects or accounts")
            session.delete(tenant)
            return True

    def create_project(
        self, tenant_id: UUID, key: str, name: str | None, metadata: dict[str, Any]
    ) -> dict:
        try:
            with self._session_factory() as session, session.begin():
                if session.get(Tenant, tenant_id) is None:
                    raise LookupError("tenant not found")
                project = Project(
                    id=uuid4(), tenant_id=tenant_id, key=key, name=name, metadata_json=metadata
                )
                session.add(project)
                session.flush()
                return self._project(project)
        except IntegrityError as error:
            raise ValueError("project key already exists for tenant") from error

    def update_project(
        self, tenant_id: UUID, key: str, values: dict[str, Any]
    ) -> dict | None:
        with self._session_factory() as session, session.begin():
            project = session.scalar(
                select(Project).where(Project.tenant_id == tenant_id, Project.key == key)
            )
            if project is None:
                return None
            if values.get("name") is not None:
                project.name = values["name"]
            if values.get("metadata") is not None:
                project.metadata_json = values["metadata"]
            project.updated_at = datetime.now(UTC)
            session.flush()
            return self._project(project)

    def delete_project(self, tenant_id: UUID, key: str) -> bool:
        with self._session_factory() as session, session.begin():
            project = session.scalar(
                select(Project).where(Project.tenant_id == tenant_id, Project.key == key)
            )
            if project is None:
                return False
            related_models = (Snapshot, Environment, KnowledgePublication)
            if any(
                session.scalar(
                    select(model.id).where(model.project_id == project.id).limit(1)
                )
                is not None
                for model in related_models
            ):
                raise ValueError("project cannot be deleted while it has snapshots or environments")
            session.delete(project)
            return True

    @staticmethod
    def _tenant(tenant: Tenant) -> dict[str, Any]:
        return {
            "id": str(tenant.id),
            "key": tenant.key,
            "name": tenant.name,
            "status": tenant.status,
            "metadata": tenant.metadata_json,
        }

    @staticmethod
    def _project(project: Project) -> dict[str, Any]:
        return {
            "id": str(project.id),
            "tenant_id": str(project.tenant_id),
            "key": project.key,
            "name": project.name,
            "active_snapshot_id": (
                str(project.active_snapshot_id) if project.active_snapshot_id else None
            ),
            "metadata": project.metadata_json,
        }
