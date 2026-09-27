import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session, sessionmaker

from core.infrastructure.postgres.models.base import Base
from core.infrastructure.postgres.models.environment import Environment
from core.infrastructure.postgres.models.project import Project
from core.infrastructure.postgres.models.tenant import Tenant
from core.infrastructure.postgres.repositories.environment_repository import (
    PostgresEnvironmentRepository,
)
from core.infrastructure.postgres.repositories.tenant_project_management_repository import (
    PostgresTenantProjectManagementRepository,
)

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is required for PostgreSQL integration tests",
)


@pytest.fixture
def postgres_repositories():
    from sqlalchemy import create_engine

    engine = create_engine(TEST_DATABASE_URL)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    tenant_id = uuid4()
    tenant_key = f"environment-test-{tenant_id.hex}"
    project_key = f"project-{tenant_id.hex}"
    with Session(engine) as session:
        session.add(
            Tenant(
                id=tenant_id,
                key=tenant_key,
                name="Project environment integration test",
                status="active",
                metadata_json={},
            )
        )
        session.commit()
    environment_repository = PostgresEnvironmentRepository(engine=engine)
    project_repository = PostgresTenantProjectManagementRepository(factory)
    yield engine, factory, tenant_id, project_key, environment_repository, project_repository
    with Session(engine) as session, session.begin():
        project_ids = select(Project.id).where(Project.tenant_id == tenant_id)
        session.execute(delete(Environment).where(Environment.tenant_id == tenant_id))
        session.execute(delete(Project).where(Project.id.in_(project_ids)))
        session.execute(delete(Tenant).where(Tenant.id == tenant_id))
    engine.dispose()


def _environment_rows(factory, tenant_id: UUID, project_key: str) -> list[Environment]:
    with factory() as session:
        return session.scalars(
            select(Environment)
            .join(Project, Project.id == Environment.project_id)
            .where(Project.tenant_id == tenant_id, Project.key == project_key)
            .order_by(Environment.name)
        ).all()


def test_environment_create_is_project_scoped_and_duplicate_safe(postgres_repositories):
    _, factory, tenant_id, project_key, environment_repository, project_repository = (
        postgres_repositories
    )
    project_repository.create_project(tenant_id, project_key, "Project", {})
    other_project = f"other-{tenant_id.hex}"
    project_repository.create_project(tenant_id, other_project, "Other", {})

    first = environment_repository.create_for_project(
        str(tenant_id), project_key, "staging"
    )
    second = environment_repository.create_for_project(
        str(tenant_id), other_project, "staging"
    )
    with pytest.raises(ValueError, match="already exists"):
        environment_repository.create_for_project(str(tenant_id), project_key, "staging")

    assert first.id != second.id
    assert [row.name for row in _environment_rows(factory, tenant_id, project_key)].count(
        "staging"
    ) == 1


def test_concurrent_duplicate_environment_creates_leave_one_row(postgres_repositories):
    _, factory, tenant_id, project_key, environment_repository, project_repository = (
        postgres_repositories
    )
    project_repository.create_project(tenant_id, project_key, "Project", {})
    barrier = Barrier(2)

    def create_environment():
        barrier.wait()
        return environment_repository.create_for_project(
            str(tenant_id), project_key, "qa-canary"
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create_environment) for _ in range(2)]
        results = []
        conflicts = 0
        for future in futures:
            try:
                results.append(future.result())
            except ValueError:
                conflicts += 1

    assert len(results) == 1
    assert conflicts == 1
    assert [row.name for row in _environment_rows(factory, tenant_id, project_key)].count(
        "qa-canary"
    ) == 1


def test_explicit_project_creation_commits_production(postgres_repositories):
    _, factory, tenant_id, project_key, _, project_repository = postgres_repositories

    project_repository.create_project(tenant_id, project_key, "Project", {})

    assert [(row.name, row.type) for row in _environment_rows(factory, tenant_id, project_key)] == [
        ("production", "production")
    ]


def test_first_publication_materialization_creates_production_once(postgres_repositories):
    _, factory, tenant_id, project_key, environment_repository, _ = postgres_repositories

    environment_repository.resolve_or_create(project_key, "development", str(tenant_id))

    assert [(row.name, row.type) for row in _environment_rows(factory, tenant_id, project_key)] == [
        ("development", "development"),
        ("production", "production"),
    ]


def test_existing_project_receiving_environment_is_not_backfilled(postgres_repositories):
    _, factory, tenant_id, project_key, environment_repository, _ = postgres_repositories
    with factory() as session:
        session.add(
            Project(
                id=uuid4(), tenant_id=tenant_id, key=project_key, name="Pre-existing"
            )
        )
        session.commit()

    environment_repository.resolve_or_create(project_key, "development", str(tenant_id))

    assert [(row.name, row.type) for row in _environment_rows(factory, tenant_id, project_key)] == [
        ("development", "development")
    ]


def test_project_and_production_roll_back_together_when_environment_insert_fails(
    postgres_repositories,
):
    engine, factory, tenant_id, project_key, _, project_repository = postgres_repositories

    def fail_environment_insert(connection, cursor, statement, parameters, context, many):
        if statement.lower().startswith("insert into environments"):
            raise RuntimeError("production persistence failed")

    event.listen(engine, "before_cursor_execute", fail_environment_insert)
    try:
        with pytest.raises(RuntimeError, match="production persistence failed"):
            project_repository.create_project(tenant_id, project_key, "Project", {})
    finally:
        event.remove(engine, "before_cursor_execute", fail_environment_insert)

    with factory() as session:
        assert session.scalar(select(Project.id).where(Project.key == project_key)) is None


def test_explicit_and_publication_project_creation_race_keeps_one_production(
    postgres_repositories,
):
    _, factory, tenant_id, project_key, environment_repository, project_repository = (
        postgres_repositories
    )
    barrier = Barrier(2)

    def create_explicitly():
        barrier.wait()
        return project_repository.create_project(tenant_id, project_key, "Project", {})

    def materialize_from_publication():
        barrier.wait()
        return environment_repository.resolve_or_create(
            project_key, "development", str(tenant_id)
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(create_explicitly),
            executor.submit(materialize_from_publication),
        ]
        for future in futures:
            try:
                future.result()
            except ValueError:
                pass

    with factory() as session:
        projects = session.scalars(
            select(Project).where(Project.tenant_id == tenant_id, Project.key == project_key)
        ).all()
    environments = _environment_rows(factory, tenant_id, project_key)
    assert len(projects) == 1
    assert [(row.name, row.type) for row in environments].count(
        ("production", "production")
    ) == 1
