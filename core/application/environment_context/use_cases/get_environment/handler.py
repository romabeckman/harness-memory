from core.application.environment_context.ports.environment_repository import (
    EnvironmentRepository,
)
from core.application.environment_context.use_cases.get_environment.inbound import (
    GetEnvironmentInput,
)
from core.application.environment_context.use_cases.get_environment.outbound import (
    GetEnvironmentOutput,
)


class GetEnvironmentHandler:
    def __init__(self, environment_repository: EnvironmentRepository) -> None:
        self._environment_repository = environment_repository

    def execute(self, input: GetEnvironmentInput) -> GetEnvironmentOutput:
        env = self._environment_repository.resolve(
            project_key=input.project_key,
            name=input.environment_name,
            tenant_id=input.tenant_id,
        )
        if env is None:
            return GetEnvironmentOutput(found=False)

        return GetEnvironmentOutput(
            found=True,
            environment_id=env.id,
            environment_name=env.name.value,
            environment_type=env.environment_type.value,
            current_snapshot_id=env.current_snapshot_id,
            entity_summary=self._environment_repository.get_entity_summary(
                env.current_snapshot_id, input.tenant_id
            )
            if env.current_snapshot_id is not None
            else None,
        )
