from core.application.environment_context.ports.environment_repository import (
    EnvironmentRepository,
)
from core.application.environment_context.ports.memory_snapshot_query_port import (
    MemorySnapshotQueryPort,
)
from core.application.environment_context.use_cases.compare_environments.inbound import (
    CompareEnvironmentsInput,
)
from core.application.environment_context.use_cases.compare_environments.outbound import (
    CompareEnvironmentsOutput,
)


class CompareEnvironmentsHandler:
    def __init__(
        self,
        environment_repository: EnvironmentRepository,
        memory_repository: MemorySnapshotQueryPort,
    ) -> None:
        self._environment_repository = environment_repository
        self._memory_repository = memory_repository

    def execute(self, input: CompareEnvironmentsInput) -> CompareEnvironmentsOutput:
        source_env = self._environment_repository.resolve(
            project_key=input.project_key,
            name=input.source_environment,
            tenant_id=input.tenant_id,
        )
        target_env = self._environment_repository.resolve(
            project_key=input.project_key,
            name=input.target_environment,
            tenant_id=input.tenant_id,
        )

        source_entities = (
            self._memory_repository.get_snapshot_entity_keys(
                source_env.current_snapshot_id, tenant_id=input.tenant_id
            )
            if source_env and source_env.current_snapshot_id
            else set()
        )
        target_entities = (
            self._memory_repository.get_snapshot_entity_keys(
                target_env.current_snapshot_id, tenant_id=input.tenant_id
            )
            if target_env and target_env.current_snapshot_id
            else set()
        )

        added_all = sorted(source_entities - target_entities)
        removed_all = sorted(target_entities - source_entities)
        unchanged_all = sorted(source_entities & target_entities)

        offset = max(0, input.offset)
        limit = max(1, input.limit)

        added_slice = tuple(added_all[offset : offset + limit])
        removed_slice = tuple(removed_all[offset : offset + limit])
        unchanged_slice = tuple(unchanged_all[offset : offset + limit])

        return CompareEnvironmentsOutput(
            source_environment=input.source_environment,
            target_environment=input.target_environment,
            added_entities=added_slice,
            removed_entities=removed_slice,
            unchanged_entities=unchanged_slice,
            total_added=len(added_all),
            total_removed=len(removed_all),
            total_unchanged=len(unchanged_all),
        )
