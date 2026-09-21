from uuid import UUID, uuid4

from core.application.environment_context.use_cases.compare_environments.handler import (
    CompareEnvironmentsHandler,
)
from core.application.environment_context.use_cases.compare_environments.inbound import (
    CompareEnvironmentsInput,
)
from core.domain.environment.aggregates.environment import Environment
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class FakeMemoryResourceRepository:
    def __init__(self, snapshots_entities: dict[UUID, set[str]]) -> None:
        self.snapshots_entities = snapshots_entities

    def get_snapshot_entity_keys(self, snapshot_id: UUID, tenant_id: str | None = None) -> set[str]:
        return self.snapshots_entities.get(snapshot_id, set())


class FakeEnvironmentRepository:
    def __init__(self, environments: list[Environment], tenant_id: str = "default") -> None:
        self.environments: dict[tuple[str, str, str], Environment] = {
            (env.project_key.value, env.name.value, tenant_id): env for env in environments
        }

    def resolve(self, project_key: str, name: str, tenant_id: str) -> Environment | None:
        return self.environments.get((project_key, name, tenant_id))

    def promote_active_snapshot(self, env_id: UUID, snap_id: UUID, tenant_id: str) -> None:
        pass


class TestCompareEnvironments:
    def test_compares_two_environments_and_returns_diff(self) -> None:
        snap_staging = uuid4()
        snap_prod = uuid4()

        env_staging = Environment(
            id=uuid4(),
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("staging"),
            current_snapshot_id=snap_staging,
        )
        env_prod = Environment(
            id=uuid4(),
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("production"),
            current_snapshot_id=snap_prod,
        )

        memory_repo = FakeMemoryResourceRepository(
            {
                snap_staging: {"GET /products", "POST /products/v2"},
                snap_prod: {"GET /products", "POST /products/v1"},
            }
        )
        env_repo = FakeEnvironmentRepository([env_staging, env_prod])

        handler = CompareEnvironmentsHandler(
            environment_repository=env_repo,
            memory_repository=memory_repo,
        )
        output = handler.execute(
            CompareEnvironmentsInput(
                project_key="catalog",
                source_environment="staging",
                target_environment="production",
                tenant_id="default",
            )
        )

        assert output.source_environment == "staging"
        assert output.target_environment == "production"
        assert output.added_entities == ("POST /products/v2",)
        assert output.removed_entities == ("POST /products/v1",)
        assert output.unchanged_entities == ("GET /products",)
        assert output.total_added == 1
        assert output.total_removed == 1
        assert output.total_unchanged == 1

    def test_bounds_output_using_limit_and_offset(self) -> None:
        snap_staging = uuid4()
        snap_prod = uuid4()

        env_staging = Environment(
            id=uuid4(),
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("staging"),
            current_snapshot_id=snap_staging,
        )
        env_prod = Environment(
            id=uuid4(),
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("production"),
            current_snapshot_id=snap_prod,
        )

        memory_repo = FakeMemoryResourceRepository(
            {
                snap_staging: {"A", "B", "C", "D"},
                snap_prod: set(),
            }
        )
        env_repo = FakeEnvironmentRepository([env_staging, env_prod])

        handler = CompareEnvironmentsHandler(
            environment_repository=env_repo,
            memory_repository=memory_repo,
        )
        output = handler.execute(
            CompareEnvironmentsInput(
                project_key="catalog",
                source_environment="staging",
                target_environment="production",
                tenant_id="default",
                limit=2,
                offset=1,
            )
        )

        assert output.total_added == 4
        assert output.added_entities == ("B", "C")
