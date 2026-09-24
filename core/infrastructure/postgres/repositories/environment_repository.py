from collections.abc import Callable
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
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
            if engine.dialect.name == "postgresql":
                engine = engine.execution_options(isolation_level="READ COMMITTED")
            session_factory = sessionmaker(bind=engine, expire_on_commit=False)
        if session_factory is None:
            raise ValueError("session_factory or engine is required")
        self._session_factory = session_factory

    def resolve_pair(self, project_key: str, source_name: str, target_name: str,
                     tenant_id: str | None) -> tuple[DomainEnvironment | None, DomainEnvironment | None]:
        statement = (
            select(ModelEnvironment)
            .join(ModelProject,
                  (ModelProject.id == ModelEnvironment.project_id) &
                  (ModelProject.tenant_id == ModelEnvironment.tenant_id))
            .where(ModelProject.key == project_key,
                   ModelEnvironment.name.in_((source_name, target_name)))
        )
        if tenant_id is not None:
            statement = statement.where(ModelEnvironment.tenant_id == tenant_id)
        with self._session_factory() as session:
            rows = session.scalars(statement).all()
        if len({row.project_id for row in rows}) > 1:
            raise ValueError("environment matches multiple tenants; provide tenant_id")
        by_name = {row.name: row for row in rows}

        def to_domain(row):
            if row is None:
                return None
            return DomainEnvironment(
                id=row.id, project_key=ProjectKey(project_key),
                name=EnvironmentName(row.name),
                environment_type=EnvironmentType(row.type)
                if row.type in EnvironmentType._value2member_map_
                else EnvironmentType.OTHER,
                current_snapshot_id=row.current_snapshot_id,
            )

        return to_domain(by_name.get(source_name)), to_domain(by_name.get(target_name))

    def resolve(
        self, project_key: str, name: str, tenant_id: str | None
    ) -> DomainEnvironment | None:
        with self._session_factory() as session:
            stmt = (
                select(ModelEnvironment)
                .join(
                    ModelProject,
                    (ModelProject.id == ModelEnvironment.project_id)
                    & (ModelProject.tenant_id == ModelEnvironment.tenant_id),
                )
                .where(ModelProject.key == project_key, ModelEnvironment.name == name)
            )
            if tenant_id is not None:
                stmt = stmt.where(ModelEnvironment.tenant_id == tenant_id)
            rows = session.scalars(stmt).all()
            if not rows:
                return None
            if len(rows) > 1:
                raise ValueError("environment matches multiple tenants; provide tenant_id")
            row = rows[0]

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

    def resolve_or_create(self, project_key: str, name: str, tenant_id: str) -> DomainEnvironment:
        existing = self.resolve(project_key, name, tenant_id)
        if existing is not None:
            return existing
        with self._session_factory() as session:
            with session.begin():
                insert = postgres_insert if session.bind.dialect.name == "postgresql" else sqlite_insert
                session.execute(
                    insert(ModelProject).values(
                        id=uuid4(), tenant_id=tenant_id, key=project_key, name=project_key,
                    ).on_conflict_do_nothing(index_elements=["tenant_id", "key"])
                )
                project = session.scalars(
                    select(ModelProject).where(
                        ModelProject.tenant_id == tenant_id,
                        ModelProject.key == project_key,
                    )
                ).first()
                if project is None:
                    raise LookupError("project insert was not visible")
                environment_type = (
                    name
                    if name in EnvironmentType._value2member_map_
                    else EnvironmentType.OTHER.value
                )
                session.execute(
                    insert(ModelEnvironment).values(
                        id=uuid4(), tenant_id=tenant_id, project_id=project.id,
                        name=name, type=environment_type,
                    ).on_conflict_do_nothing(
                        index_elements=["tenant_id", "project_id", "name"]
                    )
                )
                row = session.scalars(
                    select(ModelEnvironment).where(
                        ModelEnvironment.tenant_id == tenant_id,
                        ModelEnvironment.project_id == project.id,
                        ModelEnvironment.name == name,
                    )
                ).one()
                return DomainEnvironment(
                    id=row.id,
                    project_key=ProjectKey(project_key),
                    name=EnvironmentName(name),
                    environment_type=EnvironmentType(environment_type),
                )
