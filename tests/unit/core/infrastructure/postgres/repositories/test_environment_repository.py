from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from core.domain.environment.aggregates.environment import Environment as DomainEnvironment
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.environment.value_objects.environment_type import EnvironmentType
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey
from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.environment import Environment as ModelEnvironment
from core.infrastructure.postgres.models.project import Project as ModelProject
from core.infrastructure.postgres.repositories.environment_repository import (
    PostgresEnvironmentRepository,
)


def _seed_project(engine, tenant_id: str, key: str) -> ModelProject:
    with Session(engine) as session:
        proj = ModelProject(
            id=uuid4(),
            tenant_id=tenant_id,
            key=key,
            name=key,
        )
        session.add(proj)
        session.commit()
        session.refresh(proj)
        return proj


class TestPostgresEnvironmentRepository:
    def test_resolves_existing_environment(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        proj = _seed_project(engine, "tenant-a", "checkout")

        with Session(engine) as session:
            env_model = ModelEnvironment(
                id=uuid4(),
                tenant_id="tenant-a",
                project_id=proj.id,
                name="staging",
                type="staging",
            )
            session.add(env_model)
            session.commit()

        repo = PostgresEnvironmentRepository(engine=engine)
        resolved = repo.resolve("checkout", "staging", tenant_id="tenant-a")

        assert resolved is not None
        assert resolved.name.value == "staging"
        assert resolved.environment_type == EnvironmentType.STAGING
        assert resolved.project_key.value == "checkout"

    def test_returns_none_for_missing_or_other_tenant(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        proj = _seed_project(engine, "tenant-a", "checkout")

        with Session(engine) as session:
            env_model = ModelEnvironment(
                id=uuid4(),
                tenant_id="tenant-a",
                project_id=proj.id,
                name="staging",
                type="staging",
            )
            session.add(env_model)
            session.commit()

        repo = PostgresEnvironmentRepository(engine=engine)
        assert repo.resolve("checkout", "staging", tenant_id="tenant-b") is None
        assert repo.resolve("checkout", "production", tenant_id="tenant-a") is None

    def test_promotes_active_snapshot(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        proj = _seed_project(engine, "tenant-a", "checkout")
        env_id = uuid4()
        new_snap_id = uuid4()

        with Session(engine) as session:
            env_model = ModelEnvironment(
                id=env_id,
                tenant_id="tenant-a",
                project_id=proj.id,
                name="staging",
                type="staging",
            )
            session.add(env_model)
            session.commit()

        repo = PostgresEnvironmentRepository(engine=engine)
        repo.promote_active_snapshot(env_id, new_snap_id, tenant_id="tenant-a")

        with Session(engine) as session:
            updated = session.get(ModelEnvironment, env_id)
            assert updated.current_snapshot_id == new_snap_id
