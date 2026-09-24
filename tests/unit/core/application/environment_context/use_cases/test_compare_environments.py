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
    def __init__(self, snapshots_entities: dict[UUID, set[str] | dict[str, str]]) -> None:
        self.snapshots_entities = snapshots_entities

    def get_snapshot_entity_fingerprints(
        self, snapshot_id: UUID, tenant_id: str | None = None
    ) -> dict[str, str]:
        values = self.snapshots_entities.get(snapshot_id, set())
        if isinstance(values, dict):
            return values
        return {key: key for key in values}


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
    def test_uses_pinned_snapshot_pair_and_bounded_comparison_when_available(self) -> None:
        source_id, target_id = uuid4(), uuid4()
        seen_limits = []
        environments = [
            Environment(uuid4(), ProjectKey("catalog"), EnvironmentName("staging"),
                        current_snapshot_id=source_id),
            Environment(uuid4(), ProjectKey("catalog"), EnvironmentName("production"),
                        current_snapshot_id=target_id),
        ]

        class OptimizedMemoryRepository:
            def compare_snapshot_entities(self, source, target, tenant_id, *, offset, limit):
                assert (source, target, tenant_id, offset) == (
                    source_id, target_id, "default", 2)
                seen_limits.append(limit)
                return {"added": ("feature:new",), "removed": (), "modified": (),
                        "unchanged": (), "total_added": 3, "total_removed": 0,
                        "total_modified": 0, "total_unchanged": 0}

            def get_snapshot_entity_fingerprints(self, *_args, **_kwargs):
                raise AssertionError("full snapshot maps must not be loaded")

        handler = CompareEnvironmentsHandler(
            FakeEnvironmentRepository(environments), OptimizedMemoryRepository()
        )
        output = handler.execute(CompareEnvironmentsInput("catalog", "staging", "production",
                                                           "default", limit=1, offset=2))
        handler.execute(CompareEnvironmentsInput("catalog", "staging", "production",
                                                 "default", limit=1000, offset=2))

        assert output.added_entities == ("feature:new",)
        assert output.total_added == 3
        assert output.source_snapshot_id == source_id
        assert output.target_snapshot_id == target_id
        assert seen_limits == [1, 500]

    def test_default_and_maximum_page_size(self) -> None:
        assert CompareEnvironmentsInput("catalog", "staging", "production").limit == 100

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

    def test_detects_modified_entity_with_same_key(self) -> None:
        source_snapshot = uuid4()
        target_snapshot = uuid4()
        environments = [
            Environment(
                uuid4(),
                ProjectKey("catalog"),
                EnvironmentName("staging"),
                current_snapshot_id=source_snapshot,
            ),
            Environment(
                uuid4(),
                ProjectKey("catalog"),
                EnvironmentName("production"),
                current_snapshot_id=target_snapshot,
            ),
        ]
        handler = CompareEnvironmentsHandler(
            FakeEnvironmentRepository(environments),
            FakeMemoryResourceRepository(
                {
                    source_snapshot: {"catalog-api": "v2"},
                    target_snapshot: {"catalog-api": "v1"},
                }
            ),
        )

        output = handler.execute(
            CompareEnvironmentsInput("catalog", "staging", "production", "default")
        )

        assert output.modified_entities == ("catalog-api",)
        assert output.total_modified == 1
        assert output.unchanged_entities == ()

    def test_rejects_unknown_environment(self) -> None:
        import pytest

        handler = CompareEnvironmentsHandler(
            FakeEnvironmentRepository([]), FakeMemoryResourceRepository({})
        )

        with pytest.raises(LookupError, match="environment not found"):
            handler.execute(
                CompareEnvironmentsInput("catalog", "staging", "production", "default")
            )

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

    def test_fallback_returns_500_items_when_requested(self) -> None:
        source_id, target_id = uuid4(), uuid4()
        environments = [
            Environment(uuid4(), ProjectKey("catalog"), EnvironmentName("staging"),
                        current_snapshot_id=source_id),
            Environment(uuid4(), ProjectKey("catalog"), EnvironmentName("production"),
                        current_snapshot_id=target_id),
        ]
        repository = FakeMemoryResourceRepository({
            source_id: {f"service-{index:03}" for index in range(501)},
            target_id: set(),
        })

        output = CompareEnvironmentsHandler(
            FakeEnvironmentRepository(environments), repository,
        ).execute(CompareEnvironmentsInput("catalog", "staging", "production", limit=500))

        assert len(output.added_entities) == 500
        assert output.total_added == 501
