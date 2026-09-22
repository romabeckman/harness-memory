from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.snapshot import Snapshot
from core.infrastructure.postgres.models.tenant import Tenant


class KnowledgeReadRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session_factory = session_factory

    def tenants(self) -> list[dict]:
        with self._session_factory() as session:
            rows = session.scalars(select(Tenant).order_by(Tenant.key)).all()
            return [self._tenant(tenant) for tenant in rows]

    def tenant(self, tenant_id: str) -> dict | None:
        with self._session_factory() as session:
            tenant = session.get(Tenant, UUID(tenant_id))
            return self._tenant(tenant) if tenant is not None else None

    def projects(self, tenant_id: str | None = None) -> list[dict]:
        statement = select(Project)
        if tenant_id is not None:
            statement = statement.where(Project.tenant_id == UUID(tenant_id))
        with self._session_factory() as session:
            projects = session.scalars(statement.order_by(Project.tenant_id, Project.key)).all()
            return [self._project(project) for project in projects]

    def project(self, tenant_id: str | None, project_key: str) -> dict | None:
        statement = select(Project).where(Project.key == project_key)
        if tenant_id is not None:
            statement = statement.where(Project.tenant_id == UUID(tenant_id))
        with self._session_factory() as session:
            matches = session.scalars(statement.order_by(Project.tenant_id)).all()
            if len(matches) > 1:
                raise ValueError("project key matches multiple tenants; provide tenant_id")
            return self._project(matches[0]) if matches else None

    def snapshots(self, tenant_id: str | None, project_key: str) -> list[dict] | None:
        project = self.project(tenant_id, project_key)
        if project is None:
            return None
        with self._session_factory() as session:
            statement = select(Snapshot).where(Snapshot.project_id == UUID(project["id"]))
            if tenant_id is not None:
                statement = statement.where(Snapshot.tenant_id == UUID(tenant_id))
            rows = session.scalars(
                statement.order_by(Snapshot.created_at.desc(), Snapshot.id.desc())
            ).all()
            return [self._snapshot(snapshot, include_payload=False) for snapshot in rows]

    def snapshot(self, tenant_id: str | None, snapshot_id: UUID) -> dict | None:
        statement = select(Snapshot).where(Snapshot.id == snapshot_id)
        if tenant_id is not None:
            statement = statement.where(Snapshot.tenant_id == UUID(tenant_id))
        with self._session_factory() as session:
            snapshot = session.scalar(statement)
            return self._snapshot(snapshot, include_payload=True) if snapshot else None

    @staticmethod
    def _tenant(tenant: Tenant) -> dict:
        return {"id": str(tenant.id), "key": tenant.key, "name": tenant.name,
                "status": tenant.status}

    @staticmethod
    def _project(project: Project) -> dict:
        return {
            "id": str(project.id),
            "tenant_id": str(project.tenant_id),
            "key": project.key,
            "name": project.name,
            "active_snapshot_id": (
                str(project.active_snapshot_id) if project.active_snapshot_id else None
            ),
        }

    @staticmethod
    def _snapshot(snapshot: Snapshot, *, include_payload: bool) -> dict:
        result = {
            "id": str(snapshot.id),
            "project_id": str(snapshot.project_id),
            "tenant_id": str(snapshot.tenant_id),
            "environment_id": (
                str(snapshot.environment_id) if snapshot.environment_id else None
            ),
            "revision": snapshot.revision,
            "schema_version": snapshot.schema_version,
            "payload_hash": snapshot.payload_hash,
            "created_at": snapshot.created_at.isoformat(),
        }
        if include_payload:
            result["payload"] = snapshot.payload
        return result
