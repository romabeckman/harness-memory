from core.application.environment_context.ports.environment_history_repository import (
    EnvironmentHistoryRepository,
)
from core.application.environment_context.use_cases.get_history.inbound import GetHistoryInput


class GetHistoryHandler:
    def __init__(self, repository: EnvironmentHistoryRepository) -> None:
        self._repository = repository

    def execute(self, request: GetHistoryInput) -> dict:
        return self._repository.get_history(request)
