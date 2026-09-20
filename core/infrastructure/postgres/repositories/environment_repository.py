from collections.abc import Callable
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from core.domain.environment.aggregates.environment import Environment as DomainEnvironment
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.environment.value_objects.environment_type import EnvironmentType
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.infrastructure.postgres.models.environment import Environment as ModelEnvironment
from core.infrastructure.postgres.models.project import Project as ModelProject


class PostgresEnvironmentRepository:
    def __init__(
        self,
        session_factory: Callable[[], Session] | None = None,
        *,
        engine=None,
    ) -> None:
        if session_factory is None and engine is not None:
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def resolve(
        self, project_key: str, name: str, tenant_id: str
    ) -> DomainEnvironment | None:
        with self._session_factory() as session:
            stmt = (
                select(ModelEnvironment)
                .join(
                    ModelProject,
                    (ModelProject.id == ModelEnvironment.project_id)
                    & (ModelProject.tenant_id == ModelEnvironment.tenant_id),
                )
                .where(
                    ModelEnvironment.tenant_id == tenant_id,
                    ModelProject.key == project_key,
                    ModelEnvironment.name == name,
                )
            )
            row = session.scalars(stmt).first()
            if row is None:
                return None

            return DomainEnvironment(
                id=row.id,
                project_key=ProjectKey(project_key),
                name=EnvironmentName(row.name),
                environment_type=EnvironmentType(row.type)
                if row.type in EnvironmentType._value2member_map_
                else EnvironmentType.OTHER,
                current_snapshot_id=row.current_snapshot_id,
            )

    def promote_active_snapshot(
        self, env_id: UUID, snap_id: UUID, tenant_id: str
    ) -> None:
        with self._session_factory() as session:
            stmt = (
                update(ModelEnvironment)
                .where(
                    ModelEnvironment.id == env_id,
                    ModelEnvironment.tenant_id == tenant_id,
                )
                .values(current_snapshot_id=snap_id)
            )
            session.execute(stmt)
            session.commit()
