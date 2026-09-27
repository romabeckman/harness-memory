from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import delete, func, or_, select
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
from core.domain.environment.value_objects.environment_type import EnvironmentType


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

    def list_tenants(
        self,
        query: str | None = None,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        stmt = select(Tenant)
        count_stmt = select(func.count(Tenant.id))
        if status is not None:
            stmt = stmt.where(Tenant.status == status)
            count_stmt = count_stmt.where(Tenant.status == status)
        if query:
            pattern = f"%{query}%"
            filter_or = or_(Tenant.key.ilike(pattern), Tenant.name.ilike(pattern))
            stmt = stmt.where(filter_or)
            count_stmt = count_stmt.where(filter_or)
        with self._session_factory() as session:
            total = session.scalar(count_stmt) or 0
            rows = session.scalars(
                stmt.order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
            ).all()
            return {
                "items": [self._tenant(t) for t in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

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
        with self._session_factory() as session, session.begin():
            if session.get(Tenant, tenant_id) is None:
                raise LookupError("tenant not found")
            project = Project(
                id=uuid4(), tenant_id=tenant_id, key=key, name=name, metadata_json=metadata
            )
            session.add(project)
            try:
                session.flush()
            except IntegrityError as error:
                raise ValueError("project key already exists for tenant") from error
            session.add(
                Environment(
                    id=uuid4(),
                    tenant_id=tenant_id,
                    project_id=project.id,
                    name=EnvironmentType.PRODUCTION.value,
                    type=EnvironmentType.PRODUCTION.value,
                )
            )
            session.flush()
            return self._project(project)

    def get_project(self, tenant_id: UUID, key: str) -> dict | None:
        with self._session_factory() as session:
            project = session.scalar(
                select(Project).where(Project.tenant_id == tenant_id, Project.key == key)
            )
            return self._project(project) if project else None

    def get_project_by_key(self, key: str) -> dict | None:
        with self._session_factory() as session:
            project = session.scalar(select(Project).where(Project.key == key))
            return self._project(project) if project else None

    def list_projects(
        self,
        tenant_id: UUID | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict:
        stmt = select(Project)
        count_stmt = select(func.count(Project.id))
        if tenant_id is not None:
            stmt = stmt.where(Project.tenant_id == tenant_id)
            count_stmt = count_stmt.where(Project.tenant_id == tenant_id)
        if query:
            pattern = f"%{query}%"
            filter_or = or_(Project.key.ilike(pattern), Project.name.ilike(pattern))
            stmt = stmt.where(filter_or)
            count_stmt = count_stmt.where(filter_or)
        with self._session_factory() as session:
            total = session.scalar(count_stmt) or 0
            rows = session.scalars(
                stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
            ).all()
            return {
                "items": [self._project(p) for p in rows],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

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
            related_models = (Snapshot, KnowledgePublication)
            if any(
                session.scalar(
                    select(model.id).where(model.project_id == project.id).limit(1)
                )
                is not None
                for model in related_models
            ):
                raise ValueError("project cannot be deleted while it has snapshots or environments")
            has_non_default_environment = session.scalar(
                select(Environment.id)
                .where(
                    Environment.project_id == project.id,
                    Environment.name != EnvironmentType.PRODUCTION.value,
                )
                .limit(1)
            ) is not None
            if has_non_default_environment:
                raise ValueError("project cannot be deleted while it has snapshots or environments")
            session.execute(
                delete(Environment).where(
                    Environment.project_id == project.id,
                    Environment.tenant_id == tenant_id,
                )
            )
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
