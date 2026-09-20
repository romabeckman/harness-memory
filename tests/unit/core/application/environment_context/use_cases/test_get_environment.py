from uuid import UUID, uuid4

from core.application.environment_context.use_cases.get_environment.handler import (
    GetEnvironmentHandler,
)
from core.application.environment_context.use_cases.get_environment.inbound import (
    GetEnvironmentInput,
)
from core.domain.environment.aggregates.environment import Environment
from core.domain.environment.value_objects.environment_name import EnvironmentName
from core.domain.environment.value_objects.environment_type import EnvironmentType
from core.domain.snapshot_publication.value_objects.project_key import ProjectKey


class FakeEnvironmentRepository:
    def __init__(self, environments: list[Environment], default_tenant: str = "default") -> None:
        self.environments: dict[tuple[str, str, str], Environment] = {
            (env.project_key.value, env.name.value, default_tenant): env for env in environments
        }

    def resolve(self, project_key: str, name: str, tenant_id: str) -> Environment | None:
        return self.environments.get((project_key, name, tenant_id))

    def promote_active_snapshot(self, env_id: UUID, snap_id: UUID, tenant_id: str) -> None:
        pass


class TestGetEnvironment:
    def test_gets_existing_environment_details(self) -> None:
        env_id = uuid4()
        snap_id = uuid4()
        env = Environment(
            id=env_id,
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("staging"),
            environment_type=EnvironmentType.STAGING,
            current_snapshot_id=snap_id,
        )
        repo = FakeEnvironmentRepository([env])
        handler = GetEnvironmentHandler(repo)

        output = handler.execute(
            GetEnvironmentInput(project_key="catalog", environment_name="staging", tenant_id="default")
        )

        assert output.found is True
        assert output.environment_id == env_id
        assert output.environment_name == "staging"
        assert output.environment_type == "staging"
        assert output.current_snapshot_id == snap_id

    def test_returns_not_found_when_environment_does_not_exist(self) -> None:
        repo = FakeEnvironmentRepository([])
        handler = GetEnvironmentHandler(repo)

        output = handler.execute(
            GetEnvironmentInput(project_key="catalog", environment_name="nonexistent", tenant_id="default")
        )

        assert output.found is False
        assert output.environment_id is None

    def test_enforces_tenant_isolation(self) -> None:
        env = Environment(
            id=uuid4(),
            project_key=ProjectKey("catalog"),
            name=EnvironmentName("staging"),
            environment_type=EnvironmentType.STAGING,
        )
        repo = FakeEnvironmentRepository([env], default_tenant="tenant-a")
        handler = GetEnvironmentHandler(repo)

        output = handler.execute(
            GetEnvironmentInput(project_key="catalog", environment_name="staging", tenant_id="tenant-b")
        )

        assert output.found is False
