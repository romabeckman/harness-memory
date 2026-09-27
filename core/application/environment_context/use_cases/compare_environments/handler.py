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
        resolve_pair = getattr(self._environment_repository, "resolve_pair", None)
        if resolve_pair is not None:
            source_env, target_env = resolve_pair(
                input.project_key,
                input.source_environment,
                input.target_environment,
                input.tenant_id,
            )
        else:
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
        if source_env is None or target_env is None:
            raise LookupError("environment not found")

        compare = getattr(self._memory_repository, "compare_snapshot_entities", None)
        if (
            compare is not None
            and source_env.current_snapshot_id is not None
            and target_env.current_snapshot_id is not None
        ):
            page = compare(
                source_env.current_snapshot_id,
                target_env.current_snapshot_id,
                input.tenant_id,
                offset=max(0, input.offset),
                limit=min(500, max(1, input.limit)),
            )
            return CompareEnvironmentsOutput(
                source_environment=input.source_environment,
                target_environment=input.target_environment,
                added_entities=page["added"],
                removed_entities=page["removed"],
                modified_entities=page["modified"],
                unchanged_entities=page["unchanged"],
                total_added=page["total_added"],
                total_removed=page["total_removed"],
                total_modified=page["total_modified"],
                total_unchanged=page["total_unchanged"],
                source_snapshot_id=source_env.current_snapshot_id,
                target_snapshot_id=target_env.current_snapshot_id,
            )

        source_entities = (
            self._memory_repository.get_snapshot_entity_fingerprints(
                source_env.current_snapshot_id, tenant_id=input.tenant_id
            )
            if source_env and source_env.current_snapshot_id
            else {}
        )
        target_entities = (
            self._memory_repository.get_snapshot_entity_fingerprints(
                target_env.current_snapshot_id, tenant_id=input.tenant_id
            )
            if target_env and target_env.current_snapshot_id
            else {}
        )

        source_keys = set(source_entities)
        target_keys = set(target_entities)
        shared_keys = source_keys & target_keys
        added_all = sorted(source_keys - target_keys)
        removed_all = sorted(target_keys - source_keys)
        modified_all = sorted(
            key for key in shared_keys if source_entities[key] != target_entities[key]
        )
        unchanged_all = sorted(
            key for key in shared_keys if source_entities[key] == target_entities[key]
        )

        offset = max(0, input.offset)
        limit = min(500, max(1, input.limit))

        added_slice = tuple(added_all[offset : offset + limit])
        removed_slice = tuple(removed_all[offset : offset + limit])
        unchanged_slice = tuple(unchanged_all[offset : offset + limit])
        modified_slice = tuple(modified_all[offset : offset + limit])

        return CompareEnvironmentsOutput(
            source_environment=input.source_environment,
            target_environment=input.target_environment,
            added_entities=added_slice,
            removed_entities=removed_slice,
            unchanged_entities=unchanged_slice,
            modified_entities=modified_slice,
            total_added=len(added_all),
            total_removed=len(removed_all),
            total_unchanged=len(unchanged_all),
            total_modified=len(modified_all),
            source_snapshot_id=source_env.current_snapshot_id,
            target_snapshot_id=target_env.current_snapshot_id,
        )
